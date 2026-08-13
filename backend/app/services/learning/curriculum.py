"""ZECT Learning Expansion — curriculum seeds (D1). No second catalog platform."""

from __future__ import annotations

from typing import Any

# Internal lesson paths — attribution stays ZECT; external links remain link-only elsewhere.
CURRICULUM_PATHS: list[dict[str, Any]] = [
    {
        "key": "python-fundamentals",
        "language": "Python",
        "title": "Python Fundamentals",
        "difficulty": "beginner",
        "skills": ["Python", "functions", "testing"],
        "attribution": "ZECT Learning Expansion (internal curriculum)",
        "content_policy": "internal_lesson",
        "lessons": [
            {
                "key": "py-hello-fn",
                "order_index": 1,
                "title": "Write a pure function",
                "objective": "Return True from a named function without side effects.",
                "practice_prompt": "Implement `def ok() -> bool` that returns True. Include an assert.",
                "starter_code": "def ok():\n    # TODO: return True\n    pass\n",
                "skill_tags": ["Python", "functions"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "Name the function exactly `ok` and decide what Boolean it should return.",
                    "A function body that only `return True` satisfies this exercise.",
                    "Add `assert ok() is True` after the function to self-check.",
                ],
                # Server-only — never exposed via serialize_lesson_public
                "hidden_tests": (
                    "assert callable(ok), 'ok must be a function'\n"
                    "assert ok() is True, 'ok() must return True'\n"
                    "print('PASS')\n"
                ),
            },
            {
                "key": "py-sum-list",
                "order_index": 2,
                "title": "Sum a list",
                "objective": "Write `total(nums)` that sums integers.",
                "practice_prompt": "Implement `total(nums: list[int]) -> int`. Assert total([1,2,3]) == 6.",
                "starter_code": "def total(nums):\n    # TODO\n    pass\n",
                "skill_tags": ["Python", "functions", "lists"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "Iterate the list or use a built-in aggregator.",
                    "Keep a running sum starting at 0, add each element.",
                    "Return the accumulator; assert against [1,2,3].",
                ],
                "hidden_tests": (
                    "assert total([1, 2, 3]) == 6\n"
                    "assert total([]) == 0\n"
                    "assert total([-1, 1]) == 0\n"
                    "print('PASS')\n"
                ),
            },
            {
                "key": "py-filter-even",
                "order_index": 3,
                "title": "Filter even numbers",
                "objective": "Return only even ints from a list.",
                "practice_prompt": "Implement `evens(nums)` returning a new list of even numbers.",
                "starter_code": "def evens(nums):\n    # TODO\n    pass\n",
                "skill_tags": ["Python", "lists", "testing"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "Even numbers satisfy `n % 2 == 0`.",
                    "Build a new list with a comprehension or append loop.",
                    "Return the filtered list; do not mutate the input in place.",
                ],
                "hidden_tests": (
                    "assert evens([1, 2, 3, 4]) == [2, 4]\n"
                    "assert evens([]) == []\n"
                    "assert evens([1, 3]) == []\n"
                    "print('PASS')\n"
                ),
            },
        ],
    },
    {
        "key": "typescript-basics",
        "language": "TypeScript",
        "title": "TypeScript Basics",
        "difficulty": "beginner",
        "skills": ["TypeScript", "functions", "testing"],
        "attribution": "ZECT Learning Expansion (internal curriculum)",
        "content_policy": "internal_lesson",
        "lessons": [
            {
                "key": "ts-identity",
                "order_index": 1,
                "title": "Identity function",
                "objective": "Return the input string unchanged.",
                "practice_prompt": "Implement `function identity(s: string): string` that returns s.",
                "starter_code": "export function identity(s: string): string {\n  // TODO\n  return \"\";\n}\n",
                "skill_tags": ["TypeScript", "functions"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "The return type is string — return the parameter.",
                    "Avoid transforming the string; pass it through.",
                    "`return s;` is enough for this lesson.",
                ],
            },
            {
                "key": "ts-sum",
                "order_index": 2,
                "title": "Sum numbers",
                "objective": "Sum an array of numbers.",
                "practice_prompt": "Implement `sum(nums: number[]): number`.",
                "starter_code": "export function sum(nums: number[]): number {\n  // TODO\n  return 0;\n}\n",
                "skill_tags": ["TypeScript", "functions", "arrays"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "Use reduce or a for-loop accumulator.",
                    "Start the accumulator at 0.",
                    "Add each element and return the total.",
                ],
            },
            {
                "key": "ts-filter-truthy",
                "order_index": 3,
                "title": "Filter truthy",
                "objective": "Keep truthy values from an unknown array.",
                "practice_prompt": "Implement `truthy<T>(items: T[]): T[]` keeping truthy entries.",
                "starter_code": "export function truthy<T>(items: T[]): T[] {\n  // TODO\n  return [];\n}\n",
                "skill_tags": ["TypeScript", "arrays", "testing"],
                "difficulty": "beginner",
                "hint_ladder": [
                    "JavaScript truthiness: filter with Boolean or `!!x`.",
                    "`items.filter(Boolean)` is a common pattern (with typing care).",
                    "Return a new array; do not mutate `items`.",
                ],
            },
        ],
    },
]


def list_path_summaries() -> list[dict[str, Any]]:
    out = []
    for p in CURRICULUM_PATHS:
        out.append(
            {
                "key": p["key"],
                "language": p["language"],
                "title": p["title"],
                "difficulty": p["difficulty"],
                "skills": list(p["skills"]),
                "lesson_count": len(p["lessons"]),
                "attribution": p["attribution"],
                "content_policy": p["content_policy"],
            }
        )
    return out


def get_path(key: str) -> dict[str, Any] | None:
    k = (key or "").strip().lower()
    for p in CURRICULUM_PATHS:
        if p["key"] == k:
            return p
    return None


def get_lesson(path_key: str, lesson_key: str) -> dict[str, Any] | None:
    path = get_path(path_key)
    if not path:
        return None
    lk = (lesson_key or "").strip().lower()
    for lesson in path["lessons"]:
        if lesson["key"] == lk:
            return {**lesson, "path_key": path["key"], "language": path["language"]}
    return None


def serialize_lesson_public(lesson: dict[str, Any], *, include_hints: bool = False) -> dict[str, Any]:
    """Public lesson payload — full hint ladder withheld unless progressive hint API."""
    out = {
        "key": lesson["key"],
        "order_index": lesson["order_index"],
        "title": lesson["title"],
        "objective": lesson["objective"],
        "practice_prompt": lesson["practice_prompt"],
        "starter_code": lesson["starter_code"],
        "skill_tags": list(lesson.get("skill_tags") or []),
        "difficulty": lesson.get("difficulty") or "beginner",
        "path_key": lesson.get("path_key"),
        "language": lesson.get("language"),
        "hint_count": len(lesson.get("hint_ladder") or []),
    }
    if include_hints:
        out["hint_ladder"] = list(lesson.get("hint_ladder") or [])
    return out
