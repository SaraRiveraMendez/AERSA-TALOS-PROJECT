"""
indexers/indexar_db.py
──────────────────────
Pulls data from clean MySQL views, vectorizes it with BGE-M3,
and persists the embeddings in Milvus Lite.

Can be run directly (cron job) or imported from the API.
"""

import logging
import sys
from pathlib import Path

import mysql.connector
import pandas as pd
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_CONFIG, MODELO_EMBEDDING, MILVUS_PATH, COLECCION_DB

log = logging.getLogger(__name__)


def row_to_text(row: dict) -> str:
    branch    = row.get("idsucursal", "Unknown")
    warehouse = row.get("almacen_nombre", "Unknown")
    product   = row.get("producto_nombre", "Unknown")
    category  = row.get("categoria_nombre", "")
    diff      = row.get("diferencia_bd", 0)
    diff_amt  = row.get("difimporte_bd", 0)
    stock_phy = row.get("stockfisico", 0)
    stock_the = row.get("stockteorico_bd", 0)
    cost      = row.get("costopromedio", 0)
    date      = row.get("inventariomes_fecha", "")

    kind = "shortage" if diff < 0 else ("surplus" if diff > 0 else "exact")
    return (
        f"Branch {branch}, warehouse '{warehouse}', product '{product}' "
        f"(category: '{category}'). Date: {date}. "
        f"Theoretical stock: {stock_the}, physical stock: {stock_phy}. "
        f"Difference: {diff} units ({kind}). "
        f"Average cost: ${cost:.2f}. Amount discrepancy: ${diff_amt:.2f}."
    )

def indexar(dias: int = 90, limite: int = 5000, embedder: SentenceTransformer = None) -> dict:
    """
    Extracts, vectorizes, and indexes MySQL data into Milvus.

    Args:
        dias:     How many days back to pull data from.
        limite:   Maximum number of records to index.
        embedder: SentenceTransformer instance (created here if not provided).

    Returns:
        dict with the number of indexed records.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    query = f"""
				SELECT
						im.idsucursal,
						a.almacen_nombre,
						p.producto_nombre,
						c.categoria_nombre,
						imd.diferencia_bd,
						imd.difimporte_bd,
						imd.stockfisico,
						imd.stockteorico_bd,
						imd.costopromedio,
						im.inventariomes_fecha
				FROM vw_inventariomesdetalle_limpio imd
				JOIN vw_inventariomes_limpio im     ON im.idinventariomes = imd.idinventariomes
				JOIN almacen a                      ON a.idalmacen        = im.idalmacen
				JOIN vw_producto_limpio p           ON p.idproducto       = imd.idproducto
				LEFT JOIN vw_categoria_limpia c     ON c.idcategoria      = p.idcategoria
				WHERE im.inventariomes_fecha >= DATE_SUB(NOW(), INTERVAL {dias} DAY)
					AND imd.flag_outlier = 0
					AND imd.flag_costopromedio_cero = 0
				ORDER BY ABS(imd.difimporte_bd) DESC
				LIMIT {limite}
		"""    

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        log.warning("No records with discrepancies found in the given date range.")
        return {"indexed": 0}

    log.info(f"Vectorizing {len(df)} records...")

    if embedder is None:
        embedder = SentenceTransformer(MODELO_EMBEDDING)

    texts = [row_to_text(r) for r in df.to_dict("records")]
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    milvus = MilvusClient(MILVUS_PATH)
    if not milvus.has_collection(COLECCION_DB):
        milvus.create_collection(collection_name=COLECCION_DB, dimension=1024)

    data = [
        {"id": i, "vector": embeddings[i].tolist(), "texto": texts[i]}
        for i in range(len(texts))
    ]
    milvus.upsert(collection_name=COLECCION_DB, data=data)
    log.info(f"Indexing complete: {len(texts)} records saved to '{COLECCION_DB}'.")

    return {"indexed": len(texts)}


# ── Direct execution (cron job) ────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = indexar(dias=90, limite=10000)
    print(f"✓ {result['indexed']} records indexed.")
