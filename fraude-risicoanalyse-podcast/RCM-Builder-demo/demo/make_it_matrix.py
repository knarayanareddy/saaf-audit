"""
Bouwt een IT-dependency-matrix (it_matrix.json) uit een RCM-run plus een profiel.

Waarom dit script bestaat
-------------------------
rcm_builder.py deelt control-ID's (CTRL-0001, CTRL-0002, ...) pas uit tijdens de run,
op volgorde van de invoer. De IT-matrix koppelt op die ID's. Zodra je een risico
toevoegt of verplaatst, verschuiven alle ID's en wijst de matrix naar de verkeerde
controls. Daarom beschrijft het profiel de matrix per BRONREFERENTIE van het risico
(F-2024-03, INC-2025-131, FS-02, WNT, ...) en per positie van de control binnen dat
risico. Dit script vertaalt het profiel naar de control-ID's van een concrete run.

Profielformaat (JSON)
---------------------
{
  "F-2024-03": [ <matrixregel voor control 1>, <matrixregel voor control 2 of null> ],
  "INC-2025-131": [ <regel>, null ],
  ...
}
Een matrixregel bevat system_name, itgc_dependency_types en ipe_details, zonder
control_id (die vult dit script in). null betekent: geen matrixregel, de control
wordt in stage 3 'Not Assessed'. Sleutels die met een underscore beginnen worden
genegeerd (commentaar).

Gebruik
-------
1. Draai de pipeline een keer met een lege matrix om control-ID's te krijgen:
     python tools/scripts/rcm_builder.py --input demo/data/use_cases.json ^
         --it-matrix demo/data/_empty_matrix.json --out-json demo/outputs/_pass1.json --out-md demo/outputs/_pass1.md
2. Bouw de matrix:
     python demo/make_it_matrix.py --rcm demo/outputs/_pass1.json ^
         --profile demo/data/it_profile_basis.json --out demo/data/it_matrix_basis.json
   Met --override kun je een tweede profiel over het eerste heen leggen (what-if):
     python demo/make_it_matrix.py --rcm demo/outputs/_pass1.json ^
         --profile demo/data/it_profile_basis.json --override demo/data/it_profile_whatif.json ^
         --out demo/data/it_matrix_whatif.json
3. Draai de pipeline opnieuw met de gebouwde matrix (zie demo/README.md).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bouw it_matrix.json uit een RCM-run en een profiel per bronreferentie.")
    parser.add_argument("--rcm", required=True, help="JSON-uitvoer van rcm_builder.py (mag met lege matrix zijn gedraaid)")
    parser.add_argument("--profile", required=True, help="Profiel: matrixregels per bronreferentie")
    parser.add_argument("--override", help="Optioneel tweede profiel; sleutels hierin vervangen die uit --profile")
    parser.add_argument("--out", required=True, help="Pad voor de te schrijven it_matrix.json")
    args = parser.parse_args()

    rcm = load_json(args.rcm)
    profile = {k: v for k, v in load_json(args.profile).items() if not k.startswith("_")}
    if args.override:
        for key, value in load_json(args.override).items():
            if not key.startswith("_"):
                profile[key] = value

    rows: list[dict] = []
    unused = set(profile)
    for risk in rcm.get("risks", []):
        stage1 = risk.get("stage1", {})
        if stage1.get("uc6_generated"):
            continue
        key = next((ref for ref in stage1.get("source_references", []) if ref in profile), None)
        if key is None:
            continue
        unused.discard(key)
        controls = risk.get("stage2", {}).get("controls", [])
        for control, spec in zip(controls, profile[key]):
            if spec is None:
                continue
            rows.append({"control_id": control["control_id"], **spec})

    out = {
        "_comment": (
            "Gegenereerd door demo/make_it_matrix.py. Niet met de hand bewerken: pas het profiel aan "
            "en genereer opnieuw, anders lopen control-ID's uit de pas."
        ),
        "_generated_from": {"rcm": args.rcm, "profile": args.profile, "override": args.override or ""},
        "it_dependency_matrix": rows,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"IT-matrix geschreven: {out_path} ({len(rows)} regels)")
    if unused:
        print("Let op, niet gebruikt (referentie niet gevonden in de RCM):", ", ".join(sorted(unused)))


if __name__ == "__main__":
    main()
