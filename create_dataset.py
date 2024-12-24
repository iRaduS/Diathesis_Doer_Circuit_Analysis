import os
import json
import random

SINGULAR_SUBJECTS = [
    "wizard", "mermaid", "princess", "seamstress", "dancer",
    "archer", "jester", "rider", "emperor", "magician",
    "veteran", "scholar", "butcher", "drummer", "pilot",
    "driver", "baker", "boxer", "surgeon", "ranger",
    "nun", "scribe", "oracle", "bishop", "knight",
    "cowboy", "monk", "scout", "harvester", "baron",
]

PLURAL_SUBJECTS = [
    "wizards", "mermaids", "princesses", "seamstresses", "dancers",
    "archers", "jesters", "riders", "emperors", "magicians",
    "veterans", "scholars", "butchers", "drummers", "pilots",
    "drivers", "bakers", "boxers", "surgeons", "rangers",
    "nuns", "scribes", "oracles", "bishops", "knights",
    "cowboys", "monks", "scouts", "harvesters", "barons",
]

ALL_NOUNS = sorted(set(SINGULAR_SUBJECTS + PLURAL_SUBJECTS))

VERBS = [
    "enchanted", "guarded", "assisted", "besieged", "taught",
    "followed", "cooked", "conquered", "tended", "admired",
    "punished", "observed", "misled", "questioned", "tracked",
    "ambushed", "filmed", "haunted", "rebuilt", "evaded",
    "blessed", "cursed", "summoned", "defeated", "helped",
    "convinced", "shocked", "fascinated", "tackled", "kidnapped",
    "rescued", "pleased", "distracted", "guided", "dragged",
    "inspired",
]


def aggregator_active(agg_subj: str, verb: str, agg_doer: str):
    """
    "The <agg_subj> that <verb> the <agg_doer>"
    doer_label = agg_subj
    """
    sentence = f"The {agg_subj} that {verb} the {agg_doer}"
    doer_label = agg_subj
    return sentence, doer_label


def aggregator_passive(agg_subj: str, verb: str, aggregator_doer: str):
    """
    "The <agg_subj> that was/were <verb> by the <aggregator_doer>"
    if agg_subj in PLURAL_SUBJECTS => were, else was
    doer_label = aggregator_doer
    """
    if agg_subj in PLURAL_SUBJECTS:
        sentence = f"The {agg_subj} that were {verb} by the {aggregator_doer}"
    else:
        sentence = f"The {agg_subj} that was {verb} by the {aggregator_doer}"
    doer_label = aggregator_doer
    return sentence, doer_label


def build_lines():
    """
    We generate lines in a way that sometimes reuses the same nouns,
    sometimes uses different nouns for src vs base. We keep the same verb,
    but don't *always* do (subj1, subj2) vs (subj2, subj1).

    Approach:
      1) First gather all distinct pairs (A,B), A != B.
      2) Shuffle them.
      3) Iterate over verbs, and for each verb:
         - pick a pair (subj1, subj2) for the 'src' aggregator.
         - with some probability, pick a *different* pair (subj3, subj4) for the 'base' aggregator
           so that we do not always see exactly the same nouns in src/base.
         - produce one example with base_diathesis=passive, and one example with base_diathesis=active (the "reverse").
    """

    # All distinct pairs of nouns:
    all_pairs = []
    for i, n1 in enumerate(ALL_NOUNS):
        for j, n2 in enumerate(ALL_NOUNS):
            if n1 != n2:
                all_pairs.append((n1, n2))
    random.shuffle(all_pairs)

    lines = []

    # We'll cycle through pairs in some fixed order, but for each verb,
    # we might pick either the same or a different pair for 'base'.
    pair_index = 0
    # We'll just do a few cycles for demonstration, or do it up to some limit
    # (because otherwise it's huge). Adjust as needed.
    for verb in VERBS:
        # We'll generate maybe 40 examples per verb as an example:
        # (In practice, you might want more or fewer.)
        for _ in range(40):
            if pair_index >= len(all_pairs):
                # Reset or break
                pair_index = 0
                random.shuffle(all_pairs)

            subj1, subj2 = all_pairs[pair_index]
            pair_index += 1

            # Decide whether or not to pick a different pair for the base
            use_different = random.random() < 0.8  # 80% chance: pick a different pair
            if use_different:
                # We pick a *different* pair
                if pair_index >= len(all_pairs):
                    pair_index = 0
                    random.shuffle(all_pairs)
                subj3, subj4 = all_pairs[pair_index]
                pair_index += 1
            else:
                # reuse the same pair in reverse
                subj3, subj4 = subj2, subj1

            # line1 => aggregator_active for src, aggregator_passive for base
            src_sent, src_doer = aggregator_active(subj1, verb, subj2)
            base_sent, base_doer = aggregator_passive(subj3, verb, subj4)
            line1 = {
                "src": src_sent,
                "base": base_sent,
                "src_label": src_doer,
                "base_label": base_doer,
                "base_diathesis": "passive"  # base is passive
            }
            lines.append(line1)

            # line2 => aggregator_passive for src, aggregator_active for base
            #         But use the same pairs (subj1,subj2) for src,
            #         and (subj3,subj4) for base to keep consistency of "different" or not
            src_sent2, src_doer2 = aggregator_passive(subj1, verb, subj2)
            base_sent2, base_doer2 = aggregator_active(subj3, verb, subj4)
            line2 = {
                "src": src_sent2,
                "base": base_sent2,
                "src_label": src_doer2,
                "base_label": base_doer2,
                "base_diathesis": "active"  # base is active
            }
            lines.append(line2)

    return lines

def main():
    lines = build_lines()
    print(f"Raw lines: {len(lines)}")

    random.seed(2024)
    random.shuffle(lines)

    final_lines = lines[:533]
    print(f"Sliced to {len(final_lines)} lines.")

    train_end = 361
    val_end = train_end + 89
    train_data = final_lines[:train_end]
    val_data = final_lines[train_end:val_end]
    test_data = final_lines[val_end:]

    def to_ordered_dict(lst):
        out = {}
        for i, ex in enumerate(lst, start=1):
            ex["src_label"] = ex["src_label"].replace("the ", "")
            ex["base_label"] = ex["base_label"].replace("the ", "")
            out[str(i)] = ex
        return out

    train_dict = to_ordered_dict(train_data)
    val_dict = to_ordered_dict(val_data)
    test_dict = to_ordered_dict(test_data)

    out_dir = "final_datasets"
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "english_train_sva_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(train_dict, f, indent=4)
    with open(os.path.join(out_dir, "english_validation_sva_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(val_dict, f, indent=4)
    with open(os.path.join(out_dir, "english_test_sva_dataset.json"), "w", encoding="utf-8") as f:
        json.dump(test_dict, f, indent=4)

    print(f"Train: {len(train_dict)} -> {os.path.join(out_dir, 'english_train_sva_dataset.json')}")
    print(f"Val:   {len(val_dict)} -> {os.path.join(out_dir, 'english_validation_sva_dataset.json')}")
    print(f"Test:  {len(test_dict)} -> {os.path.join(out_dir, 'english_test_sva_dataset.json')}")
    print("Done!")

if __name__ == "__main__":
    main()