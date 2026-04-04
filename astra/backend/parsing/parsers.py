import pandas as pd
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from astra.backend.storage.models import Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionParser:
    def preview_file(self, filepath: str, nrows: int = 10) -> Dict[str, Any]:
        """Returns the first N rows and column names of a file for UI preview."""
        try:
            ext = filepath.split('.')[-1].lower()
            if ext == 'csv':
                df = pd.read_csv(filepath, nrows=nrows)
            elif ext in ['xls', 'xlsx']:
                df = pd.read_excel(filepath, nrows=nrows)
            else:
                return {"error": f"Unsupported file type: {ext}"}

            return {
                "columns": list(df.columns),
                "rows": df.replace({pd.NA: None, float('nan'): None}).to_dict(orient='records')
            }
        except Exception as e:
            logger.error(f"Failed to preview file {filepath}: {e}")
            return {"error": str(e)}

    def parse_csv(self, filepath: str, mapping: Dict[str, str] = None, date_format: str = None) -> List[Transaction]:
        try:
            df = pd.read_csv(filepath)
            return self._from_dataframe(df, mapping, date_format)
        except Exception as e:
            logger.error(f"Failed to parse CSV {filepath}: {e}")
            return []

    def parse_excel(self, filepath: str, mapping: Dict[str, str] = None, date_format: str = None) -> List[Transaction]:
        try:
            df = pd.read_excel(filepath)
            return self._from_dataframe(df, mapping, date_format)
        except Exception as e:
            logger.error(f"Failed to parse Excel {filepath}: {e}")
            return []

    def parse_text(self, filepath: str) -> List[Transaction]:
        # Very basic plain-text parser (assumes space or tab separated)
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()

            transactions = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 3:
                    try:
                        # Try to find a date and amount
                        # This is a placeholder for more complex logic
                        date_str = parts[0]
                        amount = float(parts[-1])
                        desc = " ".join(parts[1:-1])
                        transactions.append(Transaction(
                            date=datetime.fromisoformat(date_str) if "-" in date_str else datetime.now(),
                            amount=amount,
                            description=desc,
                            raw_data=line.strip()
                        ))
                    except (ValueError, IndexError):
                        continue
            return transactions
        except Exception as e:
            logger.error(f"Failed to parse text {filepath}: {e}")
            return []

    def _from_dataframe(self, df: pd.DataFrame, mapping: Dict[str, str] = None, date_format: str = None) -> List[Transaction]:
        transactions = []

        if mapping:
            date_col = mapping.get('date')
            amount_col = mapping.get('amount')
            desc_col = mapping.get('description')
            cat_col = mapping.get('category')
        else:
            # Heuristic fallback
            cols = {col.lower(): col for col in df.columns}
            date_col = next((cols[c] for c in ['date', 'transaction date', 'time'] if c in cols), None)
            amount_col = next((cols[c] for c in ['amount', 'value', 'total'] if c in cols), None)
            desc_col = next((cols[c] for c in ['description', 'memo', 'details', 'payee'] if c in cols), None)
            cat_col = next((cols[c] for c in ['category', 'type'] if c in cols), None)

        for _, row in df.iterrows():
            try:
                date_val = row[date_col] if date_col and date_col in row else None
                if date_val:
                    if isinstance(date_val, str) and date_format:
                        date_val = datetime.strptime(date_val, date_format)
                    else:
                        date_val = pd.to_datetime(date_val).to_pydatetime()
                else:
                    date_val = datetime.now()

                amount_val = float(row[amount_col]) if amount_col and amount_col in row else 0.0
                desc_val = str(row[desc_col]) if desc_col and desc_col in row else ""
                cat_val = str(row[cat_col]) if cat_col and cat_col in row else "Uncategorized"

                transactions.append(Transaction(
                    date=date_val,
                    amount=amount_val,
                    description=desc_val,
                    category=cat_val,
                    raw_data=str(row.to_dict())
                ))
            except Exception as e:
                logger.warning(f"Skipping row due to error: {e}")
                continue

        return transactions
