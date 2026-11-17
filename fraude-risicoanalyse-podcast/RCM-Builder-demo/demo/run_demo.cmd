@echo off
REM Draait de volledige demoketen vanuit de repo-root (de map met tools\scripts).
REM Gebruik: demo\run_demo.cmd
cd /d "%~dp0.."

echo [1/7] Eerste pass met lege matrix (levert control-ID's op)
python tools\scripts\rcm_builder.py --input demo\data\use_cases.json --it-matrix demo\data\_empty_matrix.json --out-json demo\outputs\_pass1.json --out-md demo\outputs\_pass1.md --schema outputs\schemas\rcm-schema.json || exit /b 1

echo [2/7] IT-matrix basis bouwen uit profiel
python demo\make_it_matrix.py --rcm demo\outputs\_pass1.json --profile demo\data\it_profile_basis.json --out demo\data\it_matrix_basis.json || exit /b 1

echo [3/7] IT-matrix what-if bouwen (basis + override)
python demo\make_it_matrix.py --rcm demo\outputs\_pass1.json --profile demo\data\it_profile_basis.json --override demo\data\it_profile_whatif.json --out demo\data\it_matrix_whatif.json || exit /b 1

echo [4/7] Pipeline basis
python tools\scripts\rcm_builder.py --input demo\data\use_cases.json --it-matrix demo\data\it_matrix_basis.json --out-json demo\outputs\basis\rcm_output.json --out-md demo\outputs\basis\rcm_output.md --schema outputs\schemas\rcm-schema.json || exit /b 1

echo [5/7] Pipeline what-if
python tools\scripts\rcm_builder.py --input demo\data\use_cases.json --it-matrix demo\data\it_matrix_whatif.json --out-json demo\outputs\whatif\rcm_output.json --out-md demo\outputs\whatif\rcm_output.md --schema outputs\schemas\rcm-schema.json || exit /b 1

echo [6/7] HTML-exports
python tools\scripts\export_html.py --input-json demo\outputs\basis\rcm_output.json --output-html demo\outputs\basis\rcm_output.html --title "RCM Zorggroep Waterlinie - basis" || exit /b 1
python tools\scripts\export_html.py --input-json demo\outputs\whatif\rcm_output.json --output-html demo\outputs\whatif\rcm_output.html --title "RCM Zorggroep Waterlinie - what-if" || exit /b 1

echo [7/7] Vergelijking basis vs what-if
python demo\compare_runs.py demo\outputs\basis\rcm_output.json demo\outputs\whatif\rcm_output.json --out-md demo\outputs\vergelijking_basis_whatif.md || exit /b 1

echo Klaar. Open demo\outputs\basis\rcm_output.html en demo\outputs\whatif\rcm_output.html
