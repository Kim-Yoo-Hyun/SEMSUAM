# Paper Card

## Problem

ObjectNav agents often rebuild or underuse semantic evidence across consecutive object queries. Multi-object navigation needs a reusable map that can support new open-vocabulary goals without restarting semantic exploration.

## Core Idea

Maintain one real-time open-vocabulary map and reuse it across object queries, while using semantic uncertainty to guide exploration toward regions likely to improve object search.

## Input / Output

- Input: RGB-D observations, pose, natural-language or category goal queries.
- Output: open-vocabulary semantic map updates and navigation decisions for sequential object goals.

## Method

The method builds a map with open-vocabulary features that can be queried for multiple objects. It uses map uncertainty and semantic evidence to decide where to explore next rather than treating every query as independent.

## Main Claims

- A single reusable open-vocabulary map can improve zero-shot multi-object navigation efficiency.
- Semantic uncertainty helps decide where to explore for unresolved object goals.

## Strengths

- Directly connects semantic map uncertainty to navigation utility.
- Multi-object setting makes prior environment-specific perception useful instead of incidental.
- Strong alignment with H001's "memory becomes action utility" direction.

## Limitations

- The primary utility is object search/exploration, not necessarily SLAM pose graph or map-pose consistency.
- Wrong-goal visit and goal-validity arbitration are not the central evaluation surface.
- Consecutive multi-object setting differs from H001's current single-goal wrong-instance arbitration probes.

## Relevance to My Research

This is one of the closest papers to H001. It suggests that semantic uncertainty can be treated as exploration utility, but H001 can still contribute by adding wrong-goal / wasted-path failure metrics and coupling semantic utility with SLAM/map-pose uncertainty.

## Follow-up Questions

- Does `OneMap` expose enough uncertainty fields to reproduce a semantic uncertainty baseline?
- Can its multi-object map reuse idea become a baseline for H001 Step 4-5?
- Does its policy distinguish uncertainty reduction from terminal goal commitment?
