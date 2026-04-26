"""
Ejemplo: Integración del Pipeline BGE-M3 con TALOS
===================================================

Muestra cómo extraer números de inventario y convertirlos a búsqueda semántica.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mysql.connector

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@dataclass
class NumeroEmpresarial:
    """Representa un dato numérico empresarial con contexto."""
    valor: float
    metrica: str  # "ventas", "merma", "score", etc.
    unidad: str   # "%", "USD", "puntos", etc.
    sucursal: str
    periodo: str
    contexto_adicional: Dict[str, Any] = None


class ConvertidorNumeroATexto:
    """
    Convierte números empresariales a descripciones en lenguaje natural.

    La contextualización es crítica:
    - Los LLMs entienden texto mejor que números aislados
    - El contexto ayuda a los embeddings a capturar significado semántico
    """

    def __init__(self, promedios: Dict[str, float] = None):
        """
        Args:
            promedios: Dict con valores promedio para comparación
                      {"ventas": 10000, "merma": 5.0, "score": 85}
        """
        self.promedios = promedios or {}

    def clasificar_merma(self, valor: float, promedio: float = None) -> str:
        """Clasifica el nivel de merma relativo."""
        if promedio:
            ratio = (valor / promedio) if promedio != 0 else 1
            if ratio > 1.5:
                return "CRÍTICA - muy superior al promedio"
            elif ratio > 1.2:
                return "ALTA - superior al promedio"
            elif ratio > 0.8:
                return "NORMAL - dentro del rango esperado"
            else:
                return "BAJA - inferior al promedio"
        return "sin contexto"

    def clasificar_score(self, valor: float) -> str:
        """Clasifica puntajes de desempeño."""
        if valor >= 90:
            return "EXCELENTE"
        elif valor >= 75:
            return "BUENO"
        elif valor >= 60:
            return "ACEPTABLE"
        else:
            return "REQUIERE MEJORA"

    def convertir(self, numero: NumeroEmpresarial) -> str:
        """
        Convierte un número empresarial a descripción natural.

        Returns:
            str: Descripción contextualizada del dato
        """
        valor = numero.valor
        metrica = numero.metrica.lower()
        unidad = numero.unidad
        sucursal = numero.sucursal
        periodo = numero.periodo

        # Contexto para comparaciones
        promedio = self.promedios.get(metrica)

        if metrica == "merma" or "merma" in metrica:
            clasificacion = self.clasificar_merma(valor, promedio)
            texto = (
                f"La sucursal {sucursal} presentó una merma del {valor}{unidad} "
                f"en {periodo}. Clasificación: {clasificacion}. "
            )
            if promedio:
                texto += f"El promedio esperado es {promedio}{unidad}."
            return texto

        elif metrica == "ventas" or "venta" in metrica:
            if promedio:
                diff = valor - promedio
                pct_diff = (diff / promedio * 100) if promedio != 0 else 0
                direction = "superó" if diff > 0 else "quedó debajo de"
                texto = (
                    f"Las ventas de {sucursal} en {periodo} fueron de {valor}{unidad}, "
                    f"lo que {direction} el promedio de {promedio}{unidad} "
                    f"(diferencia: {pct_diff:+.1f}%)."
                )
            else:
                texto = f"Las ventas de {sucursal} en {periodo} alcanzaron {valor}{unidad}."
            return texto

        elif metrica == "score" or "score" in metrica or "puntaje" in metrica:
            clasificacion = self.clasificar_score(valor)
            texto = (
                f"{sucursal} obtuvo una puntuación de {valor}{unidad} "
                f"en {periodo}. Desempeño: {clasificacion}. "
            )
            if promedio:
                texto += f"La puntuación promedio es {promedio}{unidad}."
            return texto

        elif metrica == "rotacion" or "rotación" in metrica:
            texto = (
                f"La rotación de inventario en {sucursal} fue de {valor} "
                f"en {periodo}. "
            )
            if promedio and valor > promedio:
                texto += f"Supera al promedio de {promedio}."
            return texto

        else:
            # Caso genérico
            texto = (
                f"{sucursal} registró {valor}{unidad} en {metrica} "
                f"durante {periodo}."
            )
            if promedio:
                diff_pct = ((valor - promedio) / promedio * 100) if promedio != 0 else 0
                texto += f" Variación respecto al promedio: {diff_pct:+.1f}%."
            return texto

class splitter:
    """Clase para dividir textos largos en fragmentos más pequeños."""

    def __init__(self, max_length: int = 250, overlap: int = 50):
        """
        Args:
            max_length: Longitud máxima de cada fragmento
            overlap: Número de tokens que se solapan entre fragmentos
        """
        self.max_length = max_length
        self.overlap = overlap

    def dividir(self, texto: str) -> List[str]:
        """Divide un texto en fragmentos con solapamiento."""
        palabras = texto.split()
        fragmentos = []

        start = 0
        while start < len(palabras):
            end = min(start + self.max_length, len(palabras))
            fragmento = " ".join(palabras[start:end])
            fragmentos.append(fragmento)
            start += self.max_length - self.overlap

        return fragmentos

class VectorizadorBGEM3:
    """
    Pipeline de vectorización usando BGE-M3.

    BGE-M3 es superior para:
    - Búsqueda densa (dense retrieval)
    - Búsqueda esparsa (sparse retrieval)
    - Información en múltiples idiomas
    """

    def __init__(self, modelo: str = "BAAI/bge-m3"):
        """
        Args:
            modelo: ID del modelo en HuggingFace
        """
        self.modelo_id = modelo
        self.modelo = None
        self.tokenizer = None
        self.splitter = splitter(max_length=250, overlap=50)

    def cargar_modelo(self):
        """Carga el modelo BGE-M3."""
        try:
            from sentence_transformers import SentenceTransformer
            log.info(f"Cargando modelo {self.modelo_id}...")
            self.modelo = SentenceTransformer(self.modelo_id)
            log.info(f"Modelo {self.modelo_id} cargado correctamente.")
        except ImportError:
            log.error("Instala sentence-transformers: pip install sentence-transformers")
            raise

    def vectorizar_texto(self, texto: str) -> np.ndarray:
        """
        Vectoriza un texto usando BGE-M3.
        Si el texto es largo, lo divide en fragmentos y promedia los embeddings.

        Args:
            texto: Descripción en lenguaje natural

        Returns:
            np.ndarray: Vector de embeddings (dimensionalidad: 1024)
        """
        if self.modelo is None:
            self.cargar_modelo()

        # Verificar si el texto necesita ser dividido
        palabras = texto.split()
        if len(palabras) > self.splitter.max_length:
            fragmentos = self.splitter.dividir(texto)
            embeddings_fragmentos = self.modelo.encode(fragmentos, normalize_embeddings=True)
            # Promediar los embeddings de los fragmentos
            embedding = np.mean(embeddings_fragmentos, axis=0)
        else:
            embedding = self.modelo.encode(texto, normalize_embeddings=True)

        return embedding

    def vectorizar_batch(self, textos: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Vectoriza múltiples textos eficientemente.
        Para textos largos, los divide en fragmentos y promedia los embeddings.

        Args:
            textos: Lista de descripciones
            batch_size: Tamaño del lote para procesamiento

        Returns:
            np.ndarray: Matriz de embeddings (n_textos, 1024)
        """
        if self.modelo is None:
            self.cargar_modelo()

        embeddings_list = []
        for texto in textos:
            palabras = texto.split()
            if len(palabras) > self.splitter.max_length:
                fragmentos = self.splitter.dividir(texto)
                embeddings_fragmentos = self.modelo.encode(fragmentos, normalize_embeddings=True, batch_size=batch_size)
                embedding = np.mean(embeddings_fragmentos, axis=0)
            else:
                embedding = self.modelo.encode(texto, normalize_embeddings=True)
            embeddings_list.append(embedding)

        return np.array(embeddings_list)

    def buscar_semantica(
        self,
        query: str,
        embeddings_base: np.ndarray,
        textos_base: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Busca los textos más semánticamente similares a una consulta.

        Args:
            query: Consulta en lenguaje natural
            embeddings_base: Matriz de embeddings previamente calculados
            textos_base: Textos originales correspondientes
            top_k: Número de resultados a retornar

        Returns:
            List[Tuple[str, float]]: Lista de (texto, similaridad) ordenada por similitud
        """
        if self.modelo is None:
            self.cargar_modelo()

        query_embedding = self.vectorizar_texto(query)

        if embeddings_base.ndim != 2:
            raise ValueError(
                f"Esperado embeddings_base con forma (n, d), pero se recibió {embeddings_base.shape}."
            )

        # Similitud coseno
        similaridades = np.dot(embeddings_base, query_embedding)

        # Top-k
        indices_top = np.argsort(similaridades)[::-1][:top_k]

        resultados = [
            (textos_base[i], similaridades[i])
            for i in indices_top
        ]

        return resultados


class PipelineBGEM3Completo:
    """Pipeline integrado: Números → Texto → Vectores → Búsqueda."""

    def __init__(self, promedios: Dict[str, float] = None):
        self.convertidor = ConvertidorNumeroATexto(promedios=promedios)
        self.vectorizador = VectorizadorBGEM3()
        self.historial_vectorizaciones = []

    def procesar_numeros(
        self,
        numeros: List[NumeroEmpresarial]
    ) -> Tuple[List[str], np.ndarray, pd.DataFrame]:
        """
        Procesa un lote de números empresariales.

        Args:
            numeros: Lista de NumeroEmpresarial

        Returns:
            Tuple[
                textos: Descripciones generadas
                embeddings: Vectores de dimensionalidad 1024
                df: DataFrame con metadatos
            ]
        """
        log.info(f"Convirtiendo {len(numeros)} números a texto...")
        textos = [self.convertidor.convertir(n) for n in numeros]

        log.info(f"Vectorizando {len(textos)} textos con BGE-M3...")
        embeddings = self.vectorizador.vectorizar_batch(textos)

        # Crear DataFrame con metadatos
        df = pd.DataFrame({
            "sucursal": [n.sucursal for n in numeros],
            "metrica": [n.metrica for n in numeros],
            "valor": [n.valor for n in numeros],
            "unidad": [n.unidad for n in numeros],
            "periodo": [n.periodo for n in numeros],
            "texto_contextualizado": textos,
            "embedding": [e for e in embeddings]  # Cada fila contiene el vector
        })

        # Guardar en historial
        self.historial_vectorizaciones.append({
            "timestamp": datetime.now(),
            "cantidad": len(numeros),
            "textos": textos,
            "embeddings": embeddings,
            "metadata": df
        })

        return textos, embeddings, df

    def buscar(
        self,
        query: str,
        df_datos: pd.DataFrame,
        top_k: int = 5
    ) -> pd.DataFrame:
        """
        Busca en los datos procesados usando semántica.

        Args:
            query: Consulta en lenguaje natural
                   Ejemplos: "merma alta", "sucursales con bajo desempeño"
            df_datos: DataFrame generado por procesar_numeros()
            top_k: Resultados a retornar

        Returns:
            pd.DataFrame: Resultados ordenados por similaridad semántica
        """
        textos = df_datos["texto_contextualizado"].tolist()
        embedding_list = [np.asarray(e) for e in df_datos["embedding"].tolist()]
        if len(embedding_list) == 0:
            raise ValueError("El DataFrame no contiene embeddings para realizar la búsqueda.")
        embeddings = np.vstack(embedding_list)

        log.info(f"Buscando: '{query}'")
        resultados = self.vectorizador.buscar_semantica(
            query=query,
            embeddings_base=embeddings,
            textos_base=textos,
            top_k=top_k
        )

        # Recuperar índices de resultados
        indices = [textos.index(r[0]) for r in resultados]
        df_resultados = df_datos.iloc[indices].copy()
        df_resultados["similaridad"] = [r[1] for r in resultados]

        return df_resultados.sort_values("similaridad", ascending=False)


# ═════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # 1. Definir datos numéricos empresariales
    datos_crudos = [
        NumeroEmpresarial(
            valor=12500, metrica="ventas", unidad="USD",
            sucursal="Sucursal A", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=8.2, metrica="merma", unidad="%",
            sucursal="Sucursal A", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=91, metrica="score", unidad="puntos",
            sucursal="Sucursal A", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=18500, metrica="ventas", unidad="USD",
            sucursal="Sucursal B", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=3.5, metrica="merma", unidad="%",
            sucursal="Sucursal B", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=88, metrica="score", unidad="puntos",
            sucursal="Sucursal B", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=9800, metrica="ventas", unidad="USD",
            sucursal="Sucursal C", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=12.1, metrica="merma", unidad="%",
            sucursal="Sucursal C", periodo="Enero 2024"
        ),
        NumeroEmpresarial(
            valor=65, metrica="score", unidad="puntos",
            sucursal="Sucursal C", periodo="Enero 2024"
        ),
    ]

    # 2. Valores promedio para contextualización
    promedios = {
        "ventas": 15000,
        "merma": 5.0,
        "score": 85
    }

    # 3. Inicializar pipeline
    pipeline = PipelineBGEM3Completo(promedios=promedios)

    # 4. Procesar números → Texto → Vectores
    textos, embeddings, df_datos = pipeline.procesar_numeros(datos_crudos)

    print("\n" + "="*80)
    print("PASO 1: NÚMEROS → LENGUAJE NATURAL")
    print("="*80)
    for i, texto in enumerate(textos[:3]):
        print(f"\n[{i+1}] {texto}")

    print("\n" + "="*80)
    print("PASO 2: VECTORIZACIÓN CON BGE-M3")
    print("="*80)
    print(f"Dimensionalidad de embeddings: {embeddings.shape}")
    print(f"Primeras 10 componentes del primer vector: {embeddings[0][:10]}")

    # 5. Búsqueda semántica
    print("\n" + "="*80)
    print("PASO 3: BÚSQUEDA SEMÁNTICA")
    print("="*80)

    queries = [
        "sucursales con merma alta",
        "bajo desempeño",
        "ventas superiores al promedio"
    ]

    for query in queries:
        print(f"\n--- Búsqueda: '{query}' ---")
        resultados = pipeline.buscar(query, df_datos, top_k=3)
        for idx, row in resultados.iterrows():
            print(f"  [{row['similaridad']:.3f}] {row['sucursal']} - {row['metrica']}: {row['valor']}{row['unidad']}")

    print("\n" + "="*80)
    print("✓ Pipeline completado exitosamente")
    print("="*80)


def extraer_numeros_de_talos(df_inventario: pd.DataFrame) -> list:
    """
    Extrae datos numéricos de un DataFrame de inventario TALOS.

    Convierte líneas como:
        producto='Arroz', almacen='A', diferencia=-50, merma_pct=8.2

    En objetos NumeroEmpresarial contextualizados.
    """
    numeros = []

    for idx, row in df_inventario.iterrows():
        almacen = str(row.get('almacen_nombre', 'Desconocido'))
        periodo = str(row.get('periodo', 'Actual'))

        # Merma en porcentaje
        merma_val = row.get('merma_pct', row.get('inventariomesdetalle_diferencia'))
        if pd.notna(merma_val):
            numeros.append(NumeroEmpresarial(
                valor=float(merma_val),
                metrica="merma",
                unidad="%",
                sucursal=almacen,
                periodo=periodo,
                contexto_adicional={
                    "producto": str(row.get('producto_nombre', '')),
                    "categoria": str(row.get('categoria_nombre', ''))
                }
            ))

        # Diferencia en importe
        difimporte_val = row.get('difimporte', row.get('inventariomesdetalle_difimporte'))
        if pd.notna(difimporte_val):
            numeros.append(NumeroEmpresarial(
                valor=float(difimporte_val),
                metrica="discrepancia_importe",
                unidad="USD",
                sucursal=almacen,
                periodo=periodo,
                contexto_adicional={
                    "producto": str(row.get('producto_nombre', '')),
                    "stock_fisico": float(row.get('stockfisico', 0)),
                    "stock_teorico": float(row.get('stockteorico', 0))
                }
            ))

        # Rotación de inventario (si está disponible)
        if 'rotacion' in row and pd.notna(row['rotacion']):
            numeros.append(NumeroEmpresarial(
                valor=float(row['rotacion']),
                metrica="rotacion",
                unidad="veces/mes",
                sucursal=almacen,
                periodo=periodo,
                contexto_adicional={
                    "producto": str(row.get('producto_nombre', '')),
                    "stock_actual": float(row.get('stockfisico', 0))
                }
            ))

    return numeros


def demo_con_datos_simulados():
    """Demo con datos de inventario simulados (sin conexión a BD)."""

    conn = mysql.connector.connect(
        host="localhost",
        port= 3306,
        user="root",
        password="12345678",
        database="talos_tecmty"
    )

    query = '''
    SELECT
        a.almacen_nombre,
        p.producto_nombre,
        c.categoria_nombre,
        imd.inventariomesdetalle_diferencia,
        imd.inventariomesdetalle_difimporte,
        im.inventariomes_totalimportefisico,
        im.inventariomes_faltantes
    FROM inventariomesdetalle imd
    JOIN inventariomes im ON im.idinventariomes = imd.idinventariomes
    JOIN almacen a ON a.idalmacen = im.idalmacen
    JOIN producto p ON p.idproducto = imd.idproducto
    JOIN categoria c ON c.idcategoria = p.idcategoria
    WHERE im.inventariomes_fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ORDER BY im.inventariomes_fecha DESC
    '''

    datos_inventario = pd.read_sql(query, conn)

    # Promedios esperados
    promedios = {
        "merma": datos_inventario['inventariomesdetalle_diferencia'].abs().mean(),
        "discrepancia_importe": datos_inventario['inventariomesdetalle_difimporte'].abs().mean()
    }

    # Extraer números
    print("\n" + "-"*80)
    print("Extrayendo números empresariales...")
    numeros = extraer_numeros_de_talos(datos_inventario)
    print(f"✓ {len(numeros)} datos extraídos\n")

    # Inicializar y procesar
    pipeline = PipelineBGEM3Completo(promedios=promedios)

    try:
        textos, embeddings, df_datos = pipeline.procesar_numeros(numeros)
    except ImportError as e:
        print(f"\n⚠️  {e}")
        print("\nPara usar BGE-M3, instala:")
        print("  pip install sentence-transformers")
        print("\nMostrando conversión a texto (sin vectorización):\n")

        # Mostrar solo la conversión a texto
        for i, num in enumerate(numeros[:5]):
            texto = pipeline.convertidor.convertir(num)
            print(f"{i+1}. {texto}\n")

        return

    # Mostrar resultados
    print("\n" + "="*80)
    print("TEXTOS CONTEXTUALIZADOS GENERADOS")
    print("="*80 + "\n")

    for i, texto in enumerate(textos[:5], 1):
        print(f"[{i}] {texto}")

    print(f"\n... ({len(textos) - 5} más)")

    print("\n" + "="*80)
    print("BÚSQUEDAS SEMÁNTICAS EJEMPLO")
    print("="*80)

    queries = [
        "almacenes con merma crítica",
        "discrepancias de inventario significativas",
        "productos con baja rotación",
        "problemas de control en almacén sur"
    ]

    for query in queries:
        print(f"\n📍 Búsqueda: \"{query}\"")
        print("-" * 60)

        try:
            resultados = pipeline.buscar(query, df_datos, top_k=3)
            for _, row in resultados.iterrows():
                print(f"  ✓ [{row['similaridad']:.1%}] {row['sucursal']} - "
                      f"{row['metrica']}: {row['valor']}{row['unidad']}")
        except Exception as e:
            print(f"  ⚠️  Error en búsqueda: {e}")

    print("\n" + "="*80)
    print("✓ Demo completada")
    print("="*80 + "\n")


def ejemplo_integracion_real():
    """
    Plantilla para integración real con base de datos TALOS.

    Reemplazar la conexión con tus credenciales reales.
    """

    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║    PLANTILLA: Integración Real con Base de Datos TALOS        ║
    ╚════════════════════════════════════════════════════════════════╝

    from bge_m3_pipeline import NumeroEmpresarial, PipelineBGEM3Completo
    import mysql.connector
    import pandas as pd

    # 1. Conexión a TALOS
    conn = mysql.connector.connect(
        host="localhost",
        user="valer",
        password="tu_contraseña",
        database="talos_tecmty"
    )

    # 2. Extraer datos de inventario reciente
    query = '''
    SELECT
        a.almacen_nombre,
        p.producto_nombre,
        c.categoria_nombre,
        imd.inventariomesdetalle_diferencia,
        imd.inventariomesdetalle_difimporte,
        im.inventariomes_totalimportefisico,
        im.inventariomes_faltantes
    FROM inventariomesdetalle imd
    JOIN inventariomes im ON im.idinventariomes = imd.idinventariomes
    JOIN almacen a ON a.idalmacen = im.idalmacen
    JOIN producto p ON p.idproducto = imd.idproducto
    JOIN categoria c ON c.idcategoria = p.idcategoria
    WHERE im.inventariomes_fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    ORDER BY im.inventariomes_fecha DESC
    '''

    df = pd.read_sql(query, conn)

    # 3. Calcular promedios
    promedios = {
        "merma": df['inventariomesdetalle_diferencia'].abs().mean(),
        "discrepancia_importe": df['inventariomesdetalle_difimporte'].abs().mean()
    }

    # 4. Procesar con pipeline
    numeros = extraer_numeros_de_talos(df)
    pipeline = PipelineBGEM3Completo(promedios=promedios)
    textos, embeddings, df_datos = pipeline.procesar_numeros(numeros)

    # 5. Búsquedas semánticas para auditoría
    alertas = pipeline.buscar("merma extraordinaria", df_datos, top_k=10)
    print(alertas[['sucursal', 'producto', 'similaridad']])
    """)


if __name__ == "__main__":

    # Ejecutar demo
    demo_con_datos_simulados()

    # Mostrar plantilla de integración real
    print("\n")