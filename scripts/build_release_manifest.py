from __future__ import annotations

import argparse
import json
from pathlib import Path

from suzano_aberta.lineage import LineageDataset, LineageEvent, LineageJournal, emit_lineage, new_run_id
from suzano_aberta.release import write_snapshot_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida o snapshot e gera o manifesto verificável da release.")
    parser.add_argument("--database", type=Path, default=Path("suzano-aberta.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("suzano-aberta.manifest.json"))
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--lineage", type=Path, default=Path(".suzano/release-lineage.jsonl"))
    args = parser.parse_args()

    run_id = new_run_id()
    journal = LineageJournal(args.lineage)
    dataset = LineageDataset(namespace="sqlite", name=str(args.database))
    manifest_dataset = LineageDataset(namespace="release", name=str(args.output))
    emit_lineage(
        LineageEvent(
            event_type="START",
            run_id=run_id,
            job_name="release.manifest",
            inputs=[dataset],
            outputs=[manifest_dataset],
        ),
        journal=journal,
    )
    try:
        manifest, report, digest = write_snapshot_manifest(
            args.database,
            output=args.output,
            previous_manifest=args.previous if args.previous and args.previous.exists() else None,
            lineage_run_id=run_id,
        )
    except Exception as exc:
        emit_lineage(
            LineageEvent(
                event_type="FAIL",
                run_id=run_id,
                job_name="release.manifest",
                inputs=[dataset],
                outputs=[manifest_dataset],
                run_facets={"error": {"type": type(exc).__name__, "message": str(exc)}},
            ),
            journal=journal,
        )
        raise

    emit_lineage(
        LineageEvent(
            event_type="COMPLETE",
            run_id=run_id,
            job_name="release.manifest",
            inputs=[dataset],
            outputs=[manifest_dataset],
            run_facets={
                "suzanoRelease": {
                    "manifestSha256": digest,
                    "datasetVersion": manifest.dataset_version,
                    "records": manifest.records,
                    "qualityStatus": report.status,
                    "qualityScore": report.score,
                }
            },
        ),
        journal=journal,
    )
    print(
        json.dumps(
            {
                "manifest": str(args.output),
                "manifest_sha256": digest,
                "dataset_version": manifest.dataset_version,
                "records": manifest.records,
                "sources": manifest.sources,
                "contract_status": report.status,
                "contract_score": report.score,
                "lineage_run_id": run_id,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
