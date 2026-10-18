# Synthetic correction and projection example

All names, records, run IDs and findings here are synthetic fixtures. No historical source image was read to create this case. `case-before.json` contains a source-supported report of age 23; `replacement.json` demonstrates a reread of 28. This is an example of recording a correction, not evidence about a real person.

From the package root, copy `examples/v1.4/case-before.json` to a working `case.json`, then run:

```bash
python genealogy.py reread case.json --old O1 --reading examples/v1.4/replacement.json --reason "Synthetic clearer final digit." --actor "synthetic-test" --expected-revision 0
python genealogy.py project case.json --mapping examples/v1.4/repository-map.json --tree examples/v1.4/existing-tree.json --out build/example
python genealogy.py check case.json
```

The replacement becomes the current fact. The earlier claim still quotes the old observation and is flagged for reassessment; the helper must not silently rewrite its reasoning. `case-after-reread.json` and `generated/` show this intermediate state. After a real assessment, update the conclusion's evidence references and scoped assessment, clear the review flag, and regenerate into a fresh output directory. The manual tree note survives regeneration.

For actual research use real source citations, version/run references and a reason grounded in the pixels. The CLI does not create or validate external SQLite run records. Follow the coordinator's correction guide for the complete reading and review workflow.
