#!/usr/bin/env python

from dataclasses import dataclass, astuple
from secrets import randbelow
import yaml

PARAMS_FILE = "params.yml"
ITEMS_FILE = "items.yml"


def read_params():
    try:
        with open(PARAMS_FILE) as f:
            return yaml.load(f, yaml.SafeLoader)
    except IOError:
        return {
            "nb_item": 100_000,
            "value_min": 1,
            "value_max": 1_000_000_000,
            "weight_min": 1,
            "weight_max": 10_000_000,
        }


def save_items(items):
    line()
    print("Saving to", ITEMS_FILE)
    with open(ITEMS_FILE, "w") as f:
        yaml.dump({"items": list(list(astuple(i)) for i in items)}, f)


@dataclass(frozen=True)
class Item:
    weight: int
    value: int


def line():
    print("-" * 80)


def generate_items(p):
    line()
    print(
        f"Generating {p['nb_item']:,} items,",
        f"weight: {p['weight_min']}-{p['weight_max']:,},",
        f"value: {p['value_min']}-{p['value_max']:,}",
    )
    w_min = p["weight_min"]
    w_range = p["weight_max"] - p["weight_min"] + 1
    v_min = p["value_min"]
    v_range = p["value_max"] - p["value_min"] + 1
    sitems = set()
    cardinal = p["nb_item"]
    while len(sitems) < cardinal:
        w = randbelow(w_range) + w_min
        v = w * randbelow(v_range) + v_min
        # v = w * randbelow(v_range) + randbelow(w) + v_min
        sitems.add(Item(w, v))
    return list(sitems)


def print_info_items(items):
    min_w = Item(2 ** 60, 0)
    min_v = Item(0, 2 ** 60)
    max_w = Item(0, 0)
    max_v = Item(0, 0)
    for item in items:
        # print(item)
        if item.weight > max_w.weight:
            max_w = item
        if item.weight < min_w.weight:
            min_w = item
        if item.value > max_v.value:
            max_v = item
        if item.value < min_v.value:
            min_v = item
    av_weight = sum(i.weight for i in items) / len(items)
    av_value = sum(i.value for i in items) / len(items)
    line()
    print(f"Items: {len(items):,}")
    print(f"  - max weight: {max_w}")
    print(f"  - max value : {max_v}")
    print(f"  - min weight: {min_w}")
    print(f"  - min value : {min_v}")
    print(f"  - average weight : {av_weight:.1f}")
    print(f"  - average value : {av_value:.1f}")
    print("(Remove high score file if any.)")


def main():
    p = read_params()
    items = generate_items(p)
    print_info_items(items)
    save_items(items)


if __name__ == "__main__":
    main()
