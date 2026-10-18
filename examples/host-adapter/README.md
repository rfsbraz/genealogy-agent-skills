# Reference host adapter (synthetic)

A small adapter for a made-up host project whose canonical record is text. It follows the [host adapter contract](../../skills/genealogy-mode/references/host-adapter.md). All data is synthetic and comes from the v1.4 example case.

- `host/ledger.jsonl`: the host record, one JSON record per line. The host stores the required sections and also chooses to store `searches`.
- `research/cases/C-EXAMPLE.json`: the sidecar with the working case state the host does not store, including `evidence_assessment` keyed by conclusion ID.
- `adapter.py`: `export` prints the case view, `import case.json` writes changes back.

Run the round trip check from this folder:

```bash
python ../../skills/genealogy-mode/scripts/host_adapter.py check --export "python adapter.py export" --import "python adapter.py import" --sidecar research/cases/C-EXAMPLE.json
```

This example rewrites its synthetic files on import to stay short. A real host routes import through its own reviewed write path, for example by appending ledger rows, and runs its own checks before keeping the change.
