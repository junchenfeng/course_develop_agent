"""Split run_log.csv into individual conversation files (markdown + jsonl)."""

import csv
import json
import random
import shutil
from collections import defaultdict

from agent_prompt_review.app.paths import (
    CSV_PATH,
    DATA_DIR,
    DIAGNOSIS_DIR,
    JSONL_DIR,
    MD_DIR,
    SAMPLED_DIR,
)

SAMPLE_SEED = 42
SAMPLE_COUNT = 10
MIN_MESSAGES_FOR_SAMPLE = 10
# 只保留「轮次」严格大于 5 的对话（CSV 每行 = 1 轮 user+agent）
MIN_MESSAGE_PAIRS_TO_KEEP = 5


def parse_csv():
    """Parse the CSV and group messages by conversation_id."""
    conversations = defaultdict(list)
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row["conversation_id"]
            conversations[cid].append(row)

    for cid in conversations:
        conversations[cid].sort(key=lambda r: r["start_time"])

    return conversations


def write_markdown(cid, messages, out_dir):
    """Write a single conversation as a markdown file."""
    user_id = messages[0]["user_id"]
    first_time = messages[0]["start_time"]
    last_time = messages[-1]["start_time"]
    msg_count = len(messages)

    lines = [
        f"# Conversation {cid}\n",
        f"- User: {user_id}\n",
        f"- Messages: {msg_count}\n",
        f"- Time: {first_time} ~ {last_time}\n",
        "\n---\n",
    ]

    for msg in messages:
        lines.append(f"\n## User\n{msg['input']}\n")
        lines.append(f"\n## Agent\n{msg['output']}\n")
        lines.append("\n---\n")

    path = out_dir / f"{cid}.md"
    path.write_text("".join(lines), encoding="utf-8")


def write_jsonl(cid, messages, out_dir):
    """Write a single conversation as a JSONL file."""
    path = out_dir / f"{cid}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for msg in messages:
            user_obj = {
                "role": "user",
                "content": msg["input"],
                "message_id": msg["message_id"],
                "timestamp": msg["start_time"],
            }
            agent_obj = {
                "role": "agent",
                "content": msg["output"],
                "message_id": msg["message_id"],
                "timestamp": msg["start_time"],
            }
            f.write(json.dumps(user_obj, ensure_ascii=False) + "\n")
            f.write(json.dumps(agent_obj, ensure_ascii=False) + "\n")


def sample_conversations(conversations):
    """Sample SAMPLE_COUNT conversations with >= MIN_MESSAGES_FOR_SAMPLE messages.

    Uses stratified sampling across message-count buckets and different users.
    """
    eligible = {
        cid: msgs
        for cid, msgs in conversations.items()
        if len(msgs) >= MIN_MESSAGES_FOR_SAMPLE
    }
    print(f"\nEligible conversations (>= {MIN_MESSAGES_FOR_SAMPLE} messages): {len(eligible)}")

    buckets = {"10-15": [], "16-25": [], "26-50": [], "50+": []}
    for cid, msgs in eligible.items():
        n = len(msgs)
        if n <= 15:
            buckets["10-15"].append(cid)
        elif n <= 25:
            buckets["16-25"].append(cid)
        elif n <= 50:
            buckets["26-50"].append(cid)
        else:
            buckets["50+"].append(cid)

    print("Bucket distribution:")
    for bucket, cids in buckets.items():
        print(f"  {bucket}: {len(cids)} conversations")

    rng = random.Random(SAMPLE_SEED)
    sampled = []
    seen_users = set()

    all_eligible = list(eligible.keys())
    rng.shuffle(all_eligible)

    for cid in all_eligible:
        uid = eligible[cid][0]["user_id"]
        if uid not in seen_users and len(sampled) < SAMPLE_COUNT:
            sampled.append(cid)
            seen_users.add(uid)

    if len(sampled) < SAMPLE_COUNT:
        remaining = [c for c in all_eligible if c not in sampled]
        sampled.extend(remaining[: SAMPLE_COUNT - len(sampled)])

    sampled = sampled[:SAMPLE_COUNT]
    return sampled


def filter_by_min_rounds(conversations: dict) -> dict:
    """Keep only conversations with more than MIN_MESSAGE_PAIRS_TO_KEEP rounds."""
    return {
        cid: msgs
        for cid, msgs in conversations.items()
        if len(msgs) > MIN_MESSAGE_PAIRS_TO_KEEP
    }


def prune_removed_conversation_files(allowed_ids: set[str]) -> None:
    """Delete md/jsonl/sampled/diagnosis files whose conversation_id is not kept."""
    removed = 0
    for folder in (MD_DIR, JSONL_DIR, SAMPLED_DIR, DIAGNOSIS_DIR):
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.suffix not in (".md", ".jsonl"):
                continue
            if path.stem not in allowed_ids:
                path.unlink(missing_ok=True)
                removed += 1
    print(f"\nPruned {removed} files for conversations with <= {MIN_MESSAGE_PAIRS_TO_KEEP} rounds")


def main():
    for d in [MD_DIR, JSONL_DIR, SAMPLED_DIR, DIAGNOSIS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    conversations = parse_csv()
    total_messages = sum(len(msgs) for msgs in conversations.values())
    print(f"Parsed {len(conversations)} conversations, {total_messages} message pairs")

    kept = filter_by_min_rounds(conversations)
    dropped = len(conversations) - len(kept)
    print(
        f"Keeping {len(kept)} conversations (>{MIN_MESSAGE_PAIRS_TO_KEEP} rounds); "
        f"dropping {dropped} with <= {MIN_MESSAGE_PAIRS_TO_KEEP} rounds"
    )

    prune_removed_conversation_files(set(kept.keys()))

    for cid, messages in kept.items():
        write_markdown(cid, messages, MD_DIR)
        write_jsonl(cid, messages, JSONL_DIR)

    print(f"Written {len(kept)} markdown files to {MD_DIR}")
    print(f"Written {len(kept)} jsonl files to {JSONL_DIR}")

    sampled_ids = sample_conversations(kept)
    print(f"\nSampled {len(sampled_ids)} conversations:")

    sampled_list_path = DATA_DIR / "sampled_conversations.txt"
    with open(sampled_list_path, "w") as f:
        for cid in sampled_ids:
            msgs = kept[cid]
            uid = msgs[0]["user_id"]
            print(f"  {cid} — {len(msgs)} messages, user {uid}")
            f.write(f"{cid}\n")
            src = MD_DIR / f"{cid}.md"
            dst = SAMPLED_DIR / f"{cid}.md"
            shutil.copy2(src, dst)

    print(f"\nSampled conversation IDs saved to {sampled_list_path}")
    print(f"Sampled markdown files copied to {SAMPLED_DIR}")


if __name__ == "__main__":
    main()
