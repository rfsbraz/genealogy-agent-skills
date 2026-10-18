# Synthetic v1.3 examples

All people, places, memories and archival extracts here are fictional training data. They demonstrate workflow behaviour, not real genealogy findings. The stories must never enter a real evidence graph.

- [Interview reply](interview/next-response.txt), [saved seed case](interview/case.json) and [input turn](interview/turn-001.json).
- [Novelized story](narrative/beatriz-mar.md), [passage manifest](narrative/beatriz-mar.story.json), [source case](narrative/case.json) and [supplied extracts](narrative/source-extracts.txt).

From the package root, run:

```sh
python genealogy.py check examples/v1.3/interview/case.json
python genealogy.py story check examples/v1.3/narrative/case.json examples/v1.3/narrative/beatriz-mar.story.json
```

The handoff lists its files relative to the interview folder. The `story check` command needs the v1.3 `genealogy-narrative` skill in the package.
