from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "erp": {
        "product_id",
        "onsale_web",
        "price",
        "stock_quantity",
        "stock_status",
    },
    "liaison": {
        "product_id",
        "id_web",
    },
    "web": {
        "sku",
        "post_type",
        "post_title",
        "total_sales",
    },
}

COLUMN_ORDER = {
    "erp": [
        "product_id",
        "onsale_web",
        "price",
        "stock_quantity",
        "stock_status",
    ],
    "liaison": [
        "product_id",
        "id_web",
    ],
    "web": [
        "sku",
        "post_type",
        "post_title",
        "total_sales",
    ],
}


class SourcePreparationError(Exception):
    """Erreur métier pendant la préparation des sources."""


def normalize_column_name(column: object) -> str:
    return str(column).strip().lower()


def normalize_columns(
    df: pd.DataFrame,
    source_file: Path,
) -> pd.DataFrame:
    normalized = [normalize_column_name(column) for column in df.columns]

    duplicates = sorted(
        {column for column in normalized if normalized.count(column) > 1}
    )

    if duplicates:
        raise SourcePreparationError(
            f"Le fichier '{source_file.name}' contient des colonnes "
            f"dupliquées après normalisation : {duplicates}"
        )

    result = df.copy()
    result.columns = normalized

    return result


def is_xlsx_file(path: Path) -> bool:
    """
    Détecte un fichier XLSX à partir de son contenu et non uniquement
    de son extension.

    Un fichier XLSX est une archive ZIP contenant notamment xl/.
    """
    try:
        if not zipfile.is_zipfile(path):
            return False

        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()

        return any(name.startswith("xl/") for name in names)

    except (OSError, zipfile.BadZipFile):
        return False


def read_csv_file(
    path: Path,
    nrows: int | None = None,
) -> pd.DataFrame:
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return pd.read_csv(
                path,
                sep=None,
                engine="python",
                encoding=encoding,
                dtype=str,
                nrows=nrows,
                keep_default_na=False,
            )

        except (
            UnicodeDecodeError,
            pd.errors.ParserError,
        ) as exc:
            last_error = exc

    raise SourcePreparationError(
        f"Impossible de lire '{path.name}' comme fichier CSV. Détail : {last_error}"
    )


def read_excel_file(
    path: Path,
    nrows: int | None = None,
) -> pd.DataFrame:
    try:
        return pd.read_excel(
            path,
            sheet_name=0,
            dtype=str,
            nrows=nrows,
            keep_default_na=False,
            engine="openpyxl",
        )

    except Exception as exc:
        raise SourcePreparationError(
            f"Impossible de lire '{path.name}' comme fichier XLSX. Détail : {exc}"
        ) from exc


def read_source(
    path: Path,
    nrows: int | None = None,
) -> pd.DataFrame:
    """
    Détecte le format par le contenu.

    Cela permet à Kestra de fournir les fichiers sous des noms
    techniques comme source_1, source_2 ou source_3.
    """
    if is_xlsx_file(path):
        return read_excel_file(path, nrows=nrows)

    return read_csv_file(path, nrows=nrows)


def get_columns(path: Path) -> set[str]:
    df = read_source(path, nrows=0)
    df = normalize_columns(df, path)

    return set(df.columns)


def matching_roles(columns: set[str]) -> list[str]:
    matches = []

    for role, required in REQUIRED_COLUMNS.items():
        if required.issubset(columns):
            matches.append(role)

    return matches


def candidate_files(input_dir: Path) -> list[Path]:
    """
    Sélectionne les fichiers potentiellement utilisables.

    En utilisation locale :
      *.csv / *.xlsx

    Dans Kestra :
      source_1 / source_2 / source_3
    """
    candidates = []

    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix in {".csv", ".xlsx"}:
            candidates.append(path)
            continue

        if suffix == "" and path.name.startswith("source_"):
            candidates.append(path)

    return candidates


def discover_sources(input_dir: Path) -> dict[str, Path]:
    if not input_dir.exists():
        raise SourcePreparationError(f"Le dossier d'entrée n'existe pas : {input_dir}")

    if not input_dir.is_dir():
        raise SourcePreparationError(
            f"Le chemin d'entrée n'est pas un dossier : {input_dir}"
        )

    files = candidate_files(input_dir)

    if not files:
        raise SourcePreparationError(
            f"Aucune source exploitable trouvée dans '{input_dir}'."
        )

    discovered: dict[str, Path] = {}
    unrecognized: list[tuple[Path, set[str]]] = []

    print("=== Découverte des sources ===")

    for path in files:
        try:
            columns = get_columns(path)

        except SourcePreparationError as exc:
            print(f"\nFichier ignoré : {path.name}")
            print(f"Raison : {exc}")
            continue

        matches = matching_roles(columns)

        print(f"\nFichier : {path.name}")
        print(f"Colonnes détectées : {sorted(columns)}")

        if len(matches) == 0:
            print("Rôle : non reconnu")
            unrecognized.append((path, columns))
            continue

        if len(matches) > 1:
            raise SourcePreparationError(
                f"Le fichier '{path.name}' correspond à plusieurs "
                f"sources possibles : {matches}. "
                f"Le schéma est ambigu."
            )

        role = matches[0]

        if role in discovered:
            raise SourcePreparationError(
                f"Deux fichiers correspondent à la source "
                f"'{role.upper()}' : "
                f"'{discovered[role].name}' et '{path.name}'. "
                f"Une seule source de chaque type est autorisée."
            )

        discovered[role] = path

        format_detected = "XLSX" if is_xlsx_file(path) else "CSV"

        print(f"Format détecté : {format_detected}")
        print(f"Rôle identifié : {role.upper()}")

    missing_roles = sorted(set(REQUIRED_COLUMNS) - set(discovered))

    if missing_roles:
        details = []

        for role in missing_roles:
            details.append(
                f"{role.upper()} nécessite les colonnes : "
                f"{sorted(REQUIRED_COLUMNS[role])}"
            )

        unrecognized_details = ""

        if unrecognized:
            lines = [
                f"- {path.name} : {sorted(columns)}" for path, columns in unrecognized
            ]

            unrecognized_details = "\n\nFichiers non reconnus :\n" + "\n".join(lines)

        raise SourcePreparationError(
            "Toutes les sources obligatoires n'ont pas été trouvées.\n"
            f"Sources manquantes : {missing_roles}\n\n"
            + "\n".join(details)
            + unrecognized_details
        )

    print("\n=== Sources identifiées ===")

    for role in ("erp", "liaison", "web"):
        print(f"{role.upper()} : {discovered[role].name}")

    return discovered


def prepare_source(
    role: str,
    source_path: Path,
    output_dir: Path,
) -> Path:
    df = read_source(source_path)
    df = normalize_columns(df, source_path)

    missing_columns = sorted(REQUIRED_COLUMNS[role] - set(df.columns))

    if missing_columns:
        raise SourcePreparationError(
            f"La source {role.upper()} "
            f"'{source_path.name}' ne contient pas "
            f"toutes les colonnes obligatoires. "
            f"Colonnes manquantes : {missing_columns}"
        )

    prepared = df[COLUMN_ORDER[role]].copy()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / f"{role}.csv"

    prepared.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )

    print(f"{role.upper()} préparé : {len(prepared)} lignes -> {output_path}")

    return output_path


def prepare_sources(
    input_dir: Path,
    output_dir: Path,
) -> dict[str, Path]:
    discovered = discover_sources(input_dir)

    print("\n=== Préparation des sources ===")

    outputs = {}

    for role in ("erp", "liaison", "web"):
        outputs[role] = prepare_source(
            role=role,
            source_path=discovered[role],
            output_dir=output_dir,
        )

    print("\n=== Préparation terminée ===")

    for role, output_path in outputs.items():
        print(f"{role.upper()} -> {output_path}")

    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Identifie automatiquement les sources ERP, Web "
            "et liaison à partir de leurs colonnes."
        )
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data"),
        help="Dossier contenant les sources.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("work/prepared"),
        help="Dossier de sortie des CSV normalisés.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        prepare_sources(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
        )

    except SourcePreparationError as exc:
        print(
            "\nERREUR DE PRÉPARATION DES SOURCES",
            file=sys.stderr,
        )
        print(
            exc,
            file=sys.stderr,
        )

        return 1

    except Exception as exc:
        print(
            "\nERREUR INATTENDUE",
            file=sys.stderr,
        )
        print(
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
