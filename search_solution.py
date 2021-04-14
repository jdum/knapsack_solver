#!/usr/bin/env python
"""
Knapsack Solver with basic genetic algo
Dont expect docstring!
"""

from dataclasses import dataclass, field, asdict
from typing import ClassVar
from itertools import zip_longest, chain
from secrets import choice
import yaml


defaults_params = {
    "sack_max_weight": 1_000_000_000,
    "nb_item": 100_000,
    "value_min": 1,
    "value_max": 1_000_000_000,
    "weight_min": 1,
    "weight_max": 10_000_000,
    "pool_size": 100,
    "pool_keep_winner": 1,
    "pool_keep_best": 50,
    "pool_add_random": 10,
    "pool": None,
    "item_set": None,
    "epoch": 0,
    "rounds": 100,
}

PARAMS_FILE = "params.yml"
ITEMS_FILE = "items.yml"
HIGH_SCORE = "high_score.yml"


def read_params():
    try:
        with open(PARAMS_FILE) as f:
            return yaml.load(f, yaml.SafeLoader)
    except IOError:
        return defaults_params


def read_high_score():
    try:
        with open(HIGH_SCORE) as f:
            return yaml.load(f, yaml.SafeLoader)["value"]
    except IOError:
        return 0


def dump_high_score(winner):
    with open(HIGH_SCORE, "w") as f:
        yaml.dump(winner.deep_dict(), f)


@dataclass(frozen=True)
class Item:
    # id: int
    weight: int
    value: int


def line():
    print("-" * 80)


def read_items():
    line()
    print("Reading", ITEMS_FILE)
    with open(ITEMS_FILE) as f:
        content = yaml.load(f, yaml.SafeLoader)
    # return tuple(Item(i[0], i[1], i[2]) for i in content["items"])
    return tuple(Item(i[0], i[1]) for i in content["items"])


@dataclass(frozen=False, order=True)
class Soluce:
    items: list = field(default_factory=list, init=True, compare=False)
    id: int = field(default=0, init=False, compare=False)
    weight: int = field(default=0, init=False, compare=False)
    value: int = field(default=0, init=False, compare=True)
    used_soluce_id: ClassVar[int] = 0

    def __post_init__(self):
        Soluce.used_soluce_id += 1
        self.id = Soluce.used_soluce_id
        # self.sort_items() never, it's bad.
        self.update_weight()
        self.update_value()

    def update_weight(self):
        self.weight = sum(i.weight for i in self.items) if self.items else 0

    def update_value(self):
        self.value = sum(i.value for i in self.items) if self.items else 0

    def short_repr(self):
        return (
            f"<val={self.value:,} wt={self.weight:,} qt={len(self.items)} #{self.id}>"
        )

    # def sort_items(self):
    #     self.items.sort()
    #     self.items.reverse()

    def deep_dict(self):
        d = asdict(self)
        d["items"] = [asdict(i) for i in self.items]
        return d


def gen_random_soluce(p, items):
    chosen = set()
    max_weight = p["sack_max_weight"]
    w = 0
    while True:
        i = choice(items)
        if i in chosen:
            continue
        w += i.weight
        if w > max_weight:
            break
        chosen.add(i)
    return Soluce(items=list(chosen))


def mixed_soluce(p, items, a, b):
    chosen = set()
    max_weight = p["sack_max_weight"]
    w = 0
    for i in chain(*zip_longest(a.items, b.items)):
        if i and i not in chosen:
            w += i.weight
            if w > max_weight:
                break
            chosen.add(i)
    # if we are too light, add some random:
    if w < max_weight:
        while True:
            i = choice(items)
            if i in chosen:
                continue
            w += i.weight
            if w > max_weight:
                break
            chosen.add(i)
    return Soluce(items=list(chosen))


def print_pool(pool):
    line()
    print(", ".join(s.short_repr() for s in pool))
    line()


def init_pool(p, items):
    pool = list(gen_random_soluce(p, items) for _i in range(p["pool_size"]))
    print(f"generated {len(pool)} random soluces")
    # print_pool(pool)
    return pool


def sort_pool(pool):
    return list(reversed(sorted(pool)))


def top_half_average(pool):
    top = len(pool) // 2
    return sum(i.value for i in pool[:top]) // top


def print_bests(top_average, pool):
    print(f"best of pool of {len(pool)}:")
    print("    ", pool[0].short_repr())
    print("    ", pool[1].short_repr())
    print("    ", pool[2].short_repr())
    print(f"average value top half: {top_average:,}")


def one_round(round_nb, pool, more_random, p, items):
    # selection
    pool = sort_pool(pool)
    # remove the bad scores, keep the high scores:
    pool = pool[: p["pool_keep_best"]]  # keep high scores (like keep 20%)
    # add some random to the pool, aka ~mutation, (like adding 20 random)
    qt_random = p["pool_add_random_high"] if more_random else p["pool_add_random_low"]
    for _i in range(qt_random):
        pool.append(gen_random_soluce(p, items))
    # new generation: keep the best score, generate others (99) by mixing
    # of 20 bests + 20 random
    new_pool = []
    while len(new_pool) < p["pool_size"]:
        a = choice(pool)
        b = choice(pool)
        while b == a:
            b = choice(pool)
        new_pool.append(mixed_soluce(p, items, a, b))
    pool = sort_pool(new_pool)
    line()
    print("round", round_nb)
    top_average = top_half_average(pool)
    print_bests(top_average, pool)
    return pool, top_average


def check_high_score(winner):
    high_score = read_high_score()
    line()
    print(f"Result: {winner.value:,}")
    if winner.value > high_score:
        print("This is the high score !")
        dump_high_score(winner)
    else:
        print(f"Try again! The high score is currently {high_score:,}")
    line()


def main():
    max_value = 0
    p = read_params()
    items = read_items()
    print(f"items: {len(items):,}")
    pool = init_pool(p, items)
    more_random = False
    last_average = 0
    for i in range(1, p["rounds"] + 1):
        pool, top_average = one_round(i, pool, more_random, p, items)
        more_random = bool(top_average < last_average)
        last_average = top_average
        if pool[0].value > max_value:
            winner = pool[0]
            max_value = winner.value
        print("top:", winner.short_repr())
    check_high_score(winner)


if __name__ == "__main__":
    main()
