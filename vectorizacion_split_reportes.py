"""
Script de ejemplo para procesar reportes de auditoría de inventario TALOS
usando el pipeline BGE-M3 con búsqueda semántica.

Uso:
    python vectorizacion_split_reportes.py <ruta_al_pdf>
    
Ejemplo:
    python vectorizacion_split_reportes.py "Reporte_de_Auditoría_de_Inventario.pdf"
"""

import sys
from pathlib import Path
from dataclasses import dataclass, asdict
import re
import pandas as pd
from dataclasses import asdict
import numpy as np
import logging
import PyPDF2
import camelot
import pdfplumber


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

@dataclass
class KPIInventario:
    """Representa un KPI del reporte de auditoría de inventario."""
    nombre: str
    valor: float
    unidad: str
    empresa: str
    sucursal: str
    almacen: str
    periodo: str
    descripcion: str = ""

@dataclass
class AlertaAuditoria:
    """Representa una alerta del reporte de auditoría."""
    prioridad: str  # "Alta", "Media", "Baja"
    producto: str
    categoria: str
    stock_teorico: float
    stock_fisico: float
    diferencia: float
    importe: float
    costo_prom: float = 0.0
    tipo: str = "faltante"  # "faltante" o "sobrante"

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
        """Carga el modelo BGE-M3 con optimizaciones."""
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            log.info(f"Cargando modelo {self.modelo_id}...")
            
            # Detectar dispositivo
            device = "cuda" if torch.cuda.is_available() else "cpu"
            log.info(f"Usando dispositivo: {device}")
            
            self.modelo = SentenceTransformer(self.modelo_id, device=device)
            log.info(f"Modelo {self.modelo_id} cargado correctamente en {device}.")
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


class ConvertidorAuditoria:
    """
    Convierte datos de auditoría de inventario a descripciones en lenguaje natural.
    Especializado en reportes del sistema TALOS.
    """

    def convertir_kpi(self, kpi: KPIInventario) -> str:
        """Convierte un KPI a descripción natural con prefijo."""
        texto = ""
        if "faltante" in kpi.nombre.lower():
            texto = (
                f"El almacén {kpi.almacen} de la sucursal {kpi.sucursal} "
                f"registra faltantes por {kpi.valor} {kpi.unidad} "
                f"en el período {kpi.periodo}."
            )
        elif "sobrante" in kpi.nombre.lower():
            texto = (
                f"El almacén {kpi.almacen} de la sucursal {kpi.sucursal} "
                f"presenta sobrantes por {kpi.valor} {kpi.unidad} "
                f"en el período {kpi.periodo}."
            )
        elif "físico" in kpi.nombre.lower():
            texto = (
                f"El inventario físico total del almacén {kpi.almacen} "
                f"(sucursal {kpi.sucursal}) asciende a {kpi.valor} {kpi.unidad} "
                f"para el período {kpi.periodo}."
            )
        elif "balance" in kpi.nombre.lower():
            texto = (
                f"El balance neto de inventario en {kpi.almacen} "
                f"es de {kpi.valor} {kpi.unidad}, considerando faltantes y sobrantes "
                f"({kpi.periodo})."
            )
        elif "productos" in kpi.nombre.lower():
            texto = (
                f"En el almacén {kpi.almacen} se procesaron {int(kpi.valor)} productos "
                f"en {kpi.periodo}, con estado: {kpi.descripcion}."
            )
        else:
            texto = (
                f"{kpi.nombre}: {kpi.valor} {kpi.unidad} "
                f"en {kpi.almacen} - {kpi.periodo}."
            )
        return f"KPI | {texto}"

    def convertir_alerta(self, alerta: AlertaAuditoria) -> str:
        """Convierte una alerta de auditoría a descripción natural concisa con prefijo."""
        tipo_text = "faltante" if "faltante" in alerta.tipo.lower() else "sobrante"
        texto = f"El producto {alerta.producto} tiene un {tipo_text} de {alerta.importe:.2f} USD"
        return f"{tipo_text.upper()} | {texto}"

        return texto

    def convertir_lote_alertas(self, alertas: List[AlertaAuditoria]) -> List[str]:
        """Convierte múltiples alertas a descripciones naturales."""
        return [self.convertir_alerta(alerta) for alerta in alertas]


class ExtractorReporteAuditoria:
    """
    Extrae datos del PDF de auditoría de inventario del sistema TALOS.
    """

    def __init__(self, archivo_pdf: str):
        """
        Args:
            archivo_pdf: Ruta del archivo PDF del reporte
        """
        self.archivo_pdf = archivo_pdf
        self.texto_completo = ""
        self.tablas = []
        self.kpis = []
        self.alertas_faltantes = []
        self.alertas_sobrantes = []

    def leer_pdf(self) -> str:
        """Lee el PDF y extrae texto + tablas de forma robusta."""

        if PyPDF2 is None:
            log.error("Instala PyPDF2: pip install PyPDF2")
            raise ImportError("PyPDF2 no está instalado")

        texto = ""
        tablas = []

        try:
            # =========================
            # 1. EXTRAER TEXTO BASE
            # =========================
            with open(self.archivo_pdf, 'rb') as archivo:
                lector = PyPDF2.PdfReader(archivo)

                for i, pagina in enumerate(lector.pages):
                    page_text = pagina.extract_text()
                    if page_text:
                        texto += page_text + "\n"

            log.info(f"Texto extraído: {len(texto)} caracteres")

            # =========================
            # 2. CAMELOT (si existe)
            # =========================
            if camelot is not None:
                for flavor in ["lattice", "stream"]:
                    try:
                        tables = camelot.read_pdf(
                            self.archivo_pdf,
                            pages="all",
                            flavor=flavor
                        )

                        if tables and len(tables) > 0:
                            log.info(f"Camelot ({flavor}) encontró {len(tables)} tablas")

                            for table in tables:
                                df = table.df

                                if df is None or df.empty:
                                    continue

                                tabla = []
                                for row in df.values.tolist():
                                    clean_row = [self._normalizar_celda(c) for c in row]
                                    if any(clean_row):
                                        tabla.append(clean_row)

                                if tabla:
                                    tablas.append(tabla)

                            # si ya encontró algo bueno, no seguir intentando flavors
                            break

                    except Exception as e:
                        log.warning(f"Camelot falló ({flavor}): {e}")

            # =========================
            # 3. PDFPLUMBER (fallback fuerte)
            # =========================
            if pdfplumber is not None:
                with pdfplumber.open(self.archivo_pdf) as pdf:
                    for page_number, page in enumerate(pdf.pages, 1):

                        page_tables = []

                        # método 1: extract_tables()
                        try:
                            page_tables = page.extract_tables() or []
                        except Exception:
                            page_tables = []

                        # método 2: find_tables()
                        if not page_tables:
                            try:
                                page_tables = [
                                    t.extract() for t in page.find_tables()
                                ]
                            except Exception:
                                page_tables = []

                        # método 3: extract_table() fallback único
                        if not page_tables:
                            try:
                                single = page.extract_table()
                                if single:
                                    page_tables = [single]
                            except Exception:
                                pass

                        if page_tables:
                            log.info(f"pdfplumber pág {page_number}: {len(page_tables)} tablas")

                            # fallback seguro: si la fusión falla, usa raw tables
                            cleaned = self._fusionar_tablas_pdfplumber(page_tables)

                            if cleaned and len(cleaned) > 0:
                                tablas.extend(cleaned)
                            else:
                                log.warning(f"Página {page_number}: fallback a tablas crudas")
                                tablas.extend(page_tables)
                        else:
                            log.info(f"pdfplumber pág {page_number}: sin tablas")

            # =========================
            # 4. VALIDACIÓN FINAL
            # =========================
            tablas = self._deduplicar_tablas(tablas)
            print("RAW TABLES:", page.extract_tables())
            print("FIND TABLES:", [t.extract() for t in page.find_tables()])
            print("SINGLE:", page.extract_table())
            log.info(f"TOTAL tablas antes de filtro: {len(tablas)}")

            if len(tablas) == 0:
                log.warning(
                    "NO SE EXTRAJERON TABLAS. "
                    "Probable PDF escaneado o estructura no tabular."
                )

            self.texto_completo = texto
            self.tablas = tablas

            log.info(f"Extracción final: {len(tablas)} tablas")

            return texto

        except Exception as e:
            log.error(f"Error al leer PDF: {e}")
            raise
    
    def _fusionar_tablas_pdfplumber(self, raw_tables: list) -> list:
        """Fusiona tablas fragmentadas de pdfplumber en tablas completas."""
        merged_tables = []
        current = None
        header_keywords = {"PRODUCTO", "CATEGORÍA", "CATEGORIA", "STOCK", "DIFERENCIA", "IMPORTE", "COSTO"}

        def es_header(row):
            if not row:
                return False
            joined = " ".join(self._normalizar_celda(cell).upper() for cell in row)
            return any(keyword in joined for keyword in header_keywords)

        for table in raw_tables:
            if not table:
                continue
            normalized_rows = []
            for row in table:
                if not row:
                    continue
                normalized = [self._normalizar_celda(cell) for cell in row]
                if any(normalized):
                    normalized_rows.append(normalized)

            if not normalized_rows:
                continue

            first_row = normalized_rows[0]
            if es_header(first_row):
                if current:
                    merged_tables.append(current)
                current = [first_row]
                for row in normalized_rows[1:]:
                    if len(row) == len(first_row):
                        current.append(row)
                    else:
                        merged_tables.append(current)
                        current = [row]
                continue

            if current is None:
                current = [first_row]
                for row in normalized_rows[1:]:
                    if len(row) == len(first_row):
                        current.append(row)
                    else:
                        merged_tables.append(current)
                        current = [row]
                continue

            for row in normalized_rows:
                if abs(len(row) - len(current[0])) <= 1:
                    current.append(row)
                else:
                    merged_tables.append(current)
                    current = [row]

        if current:
            merged_tables.append(current)

        return merged_tables

    def _normalizar_celda(self, valor: Any) -> str:
        if valor is None:
            return ""
        texto = str(valor).strip()
        texto = texto.replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        texto = re.sub(r"\s+", " ", texto)
        return texto

    def _parse_numero(self, valor: Any) -> Optional[float]:
        texto = self._normalizar_celda(valor)
        if not texto:
            return None
        texto = texto.replace('$', '').replace('%', '').replace(' ', '')
        texto = texto.replace(',', '')
        try:
            return float(texto)
        except ValueError:
            return None

    def _deduplicar_tablas(self, tablas: list) -> list:
        únicas = []
        seen = set()
        for tabla in tablas:
            key = tuple(tuple(row) for row in tabla)
            if key in seen:
                continue
            seen.add(key)
            únicas.append(tabla)
        return únicas

    def _buscar_indices_encabezado(self, header_row: List[str]) -> Dict[str, int]:
        encabezado = [self._normalizar_celda(celda).upper() for celda in header_row]
        indices = {}
        for idx, columna in enumerate(encabezado):
            if any(token in columna for token in ["PRODUCTO", "ARTÍCULO", "ARTICULO", "ITEM"]):
                indices['producto'] = idx
            if "CATEG" in columna:
                indices['categoria'] = idx
            if "STOCK" in columna and "TE" in columna:
                indices['stock_teorico'] = idx
            if "STOCK" in columna and "FIS" in columna:
                indices['stock_fisico'] = idx
            if "DIFERENCIA" in columna:
                indices['diferencia'] = idx
            if "IMPORTE" in columna and "DIFERENCIA" not in columna:
                indices['importe'] = idx
            if "COSTO" in columna and "PROM" in columna:
                indices['costo_prom'] = idx
        return indices

    def _extraer_alertas_desde_tablas(self, tipo: str) -> List[AlertaAuditoria]:
        alertas = []
        for tabla in self.tablas:
            if not tabla or len(tabla) < 2:
                continue

            encabezado = tabla[0]
            indices = self._buscar_indices_encabezado(encabezado)
            if 'producto' not in indices or 'categoria' not in indices or 'diferencia' not in indices or 'importe' not in indices:
                continue

            for fila in tabla[1:]:
                fila_normalizada = [self._normalizar_celda(celda) for celda in fila]
                if not any(fila_normalizada):
                    continue
                fila_texto = " ".join(fila_normalizada).upper()
                if any(keyword in fila_texto for keyword in ["TOTAL", "MEDIANA", "PROMEDIO", "MÍNIMO", "MINIMO", "MÁXIMO", "MAXIMO"]):
                    continue

                producto = fila_normalizada[indices['producto']] if indices['producto'] < len(fila_normalizada) else ""
                categoria = fila_normalizada[indices['categoria']] if indices['categoria'] < len(fila_normalizada) else ""
                diferencia = self._parse_numero(fila_normalizada[indices['diferencia']]) if indices['diferencia'] < len(fila_normalizada) else None
                importe = self._parse_numero(fila_normalizada[indices['importe']]) if indices['importe'] < len(fila_normalizada) else None
                stock_teorico = self._parse_numero(fila_normalizada[indices['stock_teorico']]) if indices.get('stock_teorico') is not None and indices['stock_teorico'] < len(fila_normalizada) else 0.0
                stock_fisico = self._parse_numero(fila_normalizada[indices['stock_fisico']]) if indices.get('stock_fisico') is not None and indices['stock_fisico'] < len(fila_normalizada) else 0.0
                costo_prom = self._parse_numero(fila_normalizada[indices['costo_prom']]) if indices.get('costo_prom') is not None and indices['costo_prom'] < len(fila_normalizada) else 0.0

                if not producto or diferencia is None or importe is None:
                    continue

                if tipo == 'faltante' and diferencia >= 0:
                    continue
                if tipo == 'sobrante' and diferencia <= 0:
                    continue

                prioridad = 'Alta' if tipo == 'faltante' else 'Media'
                alerta = AlertaAuditoria(
                    prioridad=prioridad,
                    producto=producto,
                    categoria=categoria,
                    stock_teorico=stock_teorico,
                    stock_fisico=stock_fisico,
                    diferencia=diferencia,
                    importe=importe,
                    costo_prom=costo_prom,
                    tipo=tipo
                )
                alertas.append(alerta)

        return alertas

    def extraer_kpis(self) -> List[KPIInventario]:
        """
        Extrae los KPIs principales del reporte.
        Busca patrones como: INVENTARIO FÍSICO TOTAL $93,788.65
        """
        kpis = []

        # Patrones de búsqueda para KPIs
        patrones_kpi = {
            "inventario_fisico": r"INVENTARIO FÍSICO TOTAL\s+\$?([\d,\.]+)",
            "faltantes": r"TOTAL FALTANTES\s+\$?([-\d,\.]+)",
            "sobrantes": r"TOTAL SOBRANTES\s+\$?([\d,\.]+)",
            "balance_neto": r"BALANCE NETO\s+\$?([\d,\.]+)",
            "productos_faltante": r"PRODUCTOS CON FALTANTE\s+(\d+)",
            "productos_sobrante": r"PRODUCTOS CON SOBRANTE\s+(\d+)",
            "productos_exactos": r"PRODUCTOS EXACTOS\s+(\d+)",
        }

        # Extraer información general del reporte
        match_empresa = re.search(r"EMPRESA / SUCURSAL\s+(\d+)\s*\/\s*(\d+)", self.texto_completo)
        match_almacen = re.search(r"ALMACÉN\s+([^\n]+)", self.texto_completo)
        match_periodo = re.search(r"PERÍODO AUDITADO\s+(\d{4}-\d{2}-\d{2}[^\n]*)", self.texto_completo)

        empresa = match_empresa.group(1) if match_empresa else "N/A"
        sucursal = match_empresa.group(2) if match_empresa else "N/A"
        almacen = match_almacen.group(1).strip() if match_almacen else "N/A"
        periodo = match_periodo.group(1).strip() if match_periodo else "N/A"

        # Procesar cada patrón
        for nombre_kpi, patron in patrones_kpi.items():
            match = re.search(patron, self.texto_completo)
            if match:
                valor_str = match.group(1).replace(",", "").replace("$", "").strip()
                try:
                    valor = float(valor_str)
                except ValueError:
                    continue

                # Determinar unidad
                if "faltante" in nombre_kpi.lower() or "sobrante" in nombre_kpi.lower() or "balance" in nombre_kpi.lower():
                    unidad = "USD"
                else:
                    unidad = "unidades" if "productos" in nombre_kpi else "USD"

                kpi = KPIInventario(
                    nombre=nombre_kpi.replace("_", " ").upper(),
                    valor=valor,
                    unidad=unidad,
                    empresa=empresa,
                    sucursal=sucursal,
                    almacen=almacen,
                    periodo=periodo
                )
                kpis.append(kpi)

        self.kpis = kpis
        log.info(f"Se extrajeron {len(kpis)} KPIs del reporte")
        
        # Validar consistencia de KPIs
        self.validar_kpis()
        
        return kpis

    def validar_kpis(self):
        """Valida la consistencia lógica de los KPIs extraídos."""
        # Encontrar valores relevantes
        faltantes = None
        sobrantes = None
        balance = None
        
        for kpi in self.kpis:
            nombre_lower = kpi.nombre.lower()
            if "faltante" in nombre_lower and "total" in nombre_lower:
                faltantes = kpi.valor
            elif "sobrante" in nombre_lower and "total" in nombre_lower:
                sobrantes = kpi.valor
            elif "balance" in nombre_lower and "neto" in nombre_lower:
                balance = kpi.valor
        
        if faltantes is not None and sobrantes is not None and balance is not None:
            calculado = faltantes + sobrantes
            diferencia = abs(calculado - balance)
            if diferencia > 0.01:  # Tolerancia para redondeo
                log.warning(f"Inconsistencia en KPIs: faltantes {faltantes} + sobrantes {sobrantes} = {calculado}, pero balance neto = {balance} (diferencia: {diferencia})")
            else:
                log.info("KPIs consistentes: faltantes + sobrantes ≈ balance neto")

    def extraer_alertas_faltantes(self) -> List[AlertaAuditoria]:
        """Extrae las alertas de faltantes de alto impacto usando regex mejorado."""
        alertas = []

        # Intentar extraer alertas desde tablas estructuradas primero
        alertas_tablas = self._extraer_alertas_desde_tablas(tipo='faltante')
        if alertas_tablas:
            self.alertas_faltantes = alertas_tablas
            log.info(f"Se extrajeron {len(alertas_tablas)} alertas de faltantes desde tablas estructuradas")
            return alertas_tablas

        # Buscar la sección de faltantes
        match_seccion = re.search(
            r"🔴.*?Prioridad Alta.*?Faltantes de alto impacto(.*?)(?=🟡|$)",
            self.texto_completo,
            re.DOTALL | re.IGNORECASE
        )

        if not match_seccion:
            log.warning("No se encontró sección de faltantes")
            return alertas

        seccion = match_seccion.group(1)

        # Patrón para extraer filas de productos (espacios en lugar de |)
        # Formato: número producto categoría stock_teórico stock_físico diferencia importe costo
        patron_producto = r"(\d+)\s+(.+?)\s+(Bebidas|Alimentos)\s+([\d\.,]+)\s+([\d\.,]+)\s+(-?[\d\.,]+)\s+\$?(-?[\d\.,]+)\s+\$?([\d\.,]+)"

        for match in re.finditer(patron_producto, seccion):
            try:
                numero = int(match.group(1))
                producto = match.group(2).strip()
                categoria = match.group(3).strip()
                stock_teorico = float(match.group(4).replace(",", ""))
                stock_fisico = float(match.group(5).replace(",", ""))
                diferencia = float(match.group(6).replace(",", ""))
                importe = float(match.group(7).replace(",", "").replace("$", ""))

                # Solo faltantes (diferencia negativa)
                if diferencia < 0:
                    alerta = AlertaAuditoria(
                        prioridad="Alta",
                        producto=producto,
                        categoria=categoria,
                        stock_teorico=stock_teorico,
                        stock_fisico=stock_fisico,
                        diferencia=diferencia,
                        importe=importe,
                        tipo="faltante"
                    )
                    alertas.append(alerta)
            except (ValueError, AttributeError) as e:
                continue

        self.alertas_faltantes = alertas
        log.info(f"Se extrajeron {len(alertas)} alertas de faltantes")
        return alertas

    def extraer_alertas_sobrantes(self) -> List[AlertaAuditoria]:
        """Extrae las alertas de sobrantes significativos usando regex mejorado."""
        alertas = []

        # Intentar extraer alertas desde tablas estructuradas primero
        alertas_tablas = self._extraer_alertas_desde_tablas(tipo='sobrante')
        if alertas_tablas:
            self.alertas_sobrantes = alertas_tablas
            log.info(f"Se extrajeron {len(alertas_tablas)} alertas de sobrantes desde tablas estructuradas")
            return alertas_tablas

        # Buscar la sección de sobrantes
        match_seccion = re.search(
            r"🟡.*?Prioridad Media.*?Sobrantes significativos(.*?)(?=🟢|$)",
            self.texto_completo,
            re.DOTALL | re.IGNORECASE
        )

        if not match_seccion:
            log.warning("No se encontró sección de sobrantes")
            return alertas

        seccion = match_seccion.group(1)

        # Patrón para extraer filas de productos (espacios)
        # Formato: número producto categoría stock_teórico stock_físico diferencia importe
        patron_producto = r"(\d+)\s+(.+?)\s+(Bebidas|Alimentos)\s+(-?[\d\.,]+)\s+([\d\.,]+)\s+([\d\.,]+)\s+\$?([\d\.,]+)"

        for match in re.finditer(patron_producto, seccion):
            try:
                numero = int(match.group(1))
                producto = match.group(2).strip()
                categoria = match.group(3).strip()
                stock_teorico = float(match.group(4).replace(",", ""))
                stock_fisico = float(match.group(5).replace(",", ""))
                diferencia = float(match.group(6).replace(",", ""))
                importe = float(match.group(7).replace(",", "").replace("$", ""))

                # Solo sobrantes (diferencia positiva)
                if diferencia > 0:
                    alerta = AlertaAuditoria(
                        prioridad="Media",
                        producto=producto,
                        categoria=categoria,
                        stock_teorico=stock_teorico,
                        stock_fisico=stock_fisico,
                        diferencia=diferencia,
                        importe=importe,
                        tipo="sobrante"
                    )
                    alertas.append(alerta)
            except (ValueError, AttributeError) as e:
                continue

        self.alertas_sobrantes = alertas
        log.info(f"Se extrajeron {len(alertas)} alertas de sobrantes")
        return alertas

    def procesar_reporte_completo(self) -> Dict[str, Any]:
        """Procesa el reporte completo y retorna toda la información extraída."""
        self.leer_pdf()
        self.extraer_kpis()
        self.extraer_alertas_faltantes()
        self.extraer_alertas_sobrantes()

        return {
            "kpis": self.kpis,
            "alertas_faltantes": self.alertas_faltantes,
            "alertas_sobrantes": self.alertas_sobrantes,
            "tablas": self.tablas,
            "total_alertas": len(self.alertas_faltantes) + len(self.alertas_sobrantes)
        }




class PipelineAuditoriaCompleto:
    """
    Pipeline integrado para reportes de auditoría de inventario:
    PDF → Datos → Texto Natural → Vectores → Búsqueda Semántica
    """

    def __init__(self):
        self.extractor = None
        self.convertidor_auditoria = ConvertidorAuditoria()
        self.vectorizador = VectorizadorBGEM3()
        self.historial_procesamientos = []

    def procesar_reporte_pdf(self, ruta_pdf: str) -> Dict[str, Any]:
        """
        Procesa un PDF de auditoría de inventario.

        Args:
            ruta_pdf: Ruta al archivo PDF del reporte

        Returns:
            Dict con KPIs, alertas y datos procesados
        """
        log.info(f"Procesando reporte: {ruta_pdf}")
        self.extractor = ExtractorReporteAuditoria(ruta_pdf)
        datos = self.extractor.procesar_reporte_completo()

        log.info(f"Datos extraídos: {datos['total_alertas']} alertas, {len(datos['kpis'])} KPIs")
        return datos

    def convertir_datos_a_textos(self, datos: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Convierte KPIs y alertas a descripciones en lenguaje natural.

        Args:
            datos: Dict retornado por procesar_reporte_pdf

        Returns:
            Dict con listas de textos naturales para cada sección
        """
        textos = {
            "kpis": [],
            "alertas_faltantes": [],
            "alertas_sobrantes": []
        }

        # Convertir KPIs
        for kpi in datos.get("kpis", []):
            texto = self.convertidor_auditoria.convertir_kpi(kpi)
            textos["kpis"].append(texto)

        # Convertir alertas de faltantes
        for alerta in datos.get("alertas_faltantes", []):
            texto = self.convertidor_auditoria.convertir_alerta(alerta)
            textos["alertas_faltantes"].append(texto)

        # Convertir alertas de sobrantes
        for alerta in datos.get("alertas_sobrantes", []):
            texto = self.convertidor_auditoria.convertir_alerta(alerta)
            textos["alertas_sobrantes"].append(texto)

        log.info(f"Textos generados: {len(textos['kpis'])} KPIs, "
                f"{len(textos['alertas_faltantes'])} faltantes, "
                f"{len(textos['alertas_sobrantes'])} sobrantes")

        return textos

    def vectorizar_datos(self, datos: Dict[str, Any]) -> pd.DataFrame:
        """
        Vectoriza todos los datos del reporte usando BGE-M3.

        Args:
            datos: Dict retornado por procesar_reporte_pdf

        Returns:
            pd.DataFrame con vectores y metadatos
        """
        registros = []

        # Vectorizar KPIs
        for kpi in datos.get("kpis", []):
            texto = self.convertidor_auditoria.convertir_kpi(kpi)
            embedding = self.vectorizador.vectorizar_texto(texto)
            registros.append({
                "tipo": "KPI",
                "nombre": kpi.nombre,
                "valor": kpi.valor,
                "unidad": kpi.unidad,
                "almacen": kpi.almacen,
                "periodo": kpi.periodo,
                "texto": texto,
                "embedding": embedding
            })

        # Vectorizar alertas de faltantes
        for alerta in datos.get("alertas_faltantes", []):
            texto = self.convertidor_auditoria.convertir_alerta(alerta)
            embedding = self.vectorizador.vectorizar_texto(texto)
            registros.append({
                "tipo": "FALTANTE",
                "producto": alerta.producto,
                "categoria": alerta.categoria,
                "diferencia": alerta.diferencia,
                "importe": alerta.importe,
                "prioridad": alerta.prioridad,
                "texto": texto,
                "embedding": embedding
            })

        # Vectorizar alertas de sobrantes
        for alerta in datos.get("alertas_sobrantes", []):
            texto = self.convertidor_auditoria.convertir_alerta(alerta)
            embedding = self.vectorizador.vectorizar_texto(texto)
            registros.append({
                "tipo": "SOBRANTE",
                "producto": alerta.producto,
                "categoria": alerta.categoria,
                "diferencia": alerta.diferencia,
                "importe": alerta.importe,
                "prioridad": alerta.prioridad,
                "texto": texto,
                "embedding": embedding
            })

        df = pd.DataFrame(registros)
        log.info(f"Se vectorizaron {len(df)} registros")

        # Guardar en historial
        self.historial_procesamientos.append({
            "timestamp": datetime.now(),
            "cantidad_registros": len(df),
            "dataframe": df
        })

        return df

    def buscar_semantica(
        self,
        query: str,
        df_vectorizado: pd.DataFrame,
        top_k: int = 5,
        filtro_tipo: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Busca en los datos vectorizados usando semántica.

        Args:
            query: Consulta en lenguaje natural
                   Ejemplos: "productos con mayor faltante", "bebidas con problemas",
                            "balance de inventario", "diferencias críticas"
            df_vectorizado: DataFrame generado por vectorizar_datos
            top_k: Número de resultados a retornar
            filtro_tipo: Opcional - filtrar por tipo ("KPI", "FALTANTE", "SOBRANTE")

        Returns:
            pd.DataFrame: Resultados ordenados por similaridad semántica
        """
        # Aplicar filtro si se especifica
        df_busqueda = df_vectorizado
        if filtro_tipo:
            df_busqueda = df_vectorizado[df_vectorizado["tipo"] == filtro_tipo]
            log.info(f"Filtrando por tipo: {filtro_tipo} ({len(df_busqueda)} registros)")

        if len(df_busqueda) == 0:
            log.warning(f"No se encontraron registros del tipo {filtro_tipo}")
            return pd.DataFrame()

        textos = df_busqueda["texto"].tolist()
        embeddings_list = [np.asarray(e) for e in df_busqueda["embedding"].tolist()]
        embeddings = np.vstack(embeddings_list)

        log.info(f"Buscando: '{query}'")
        resultados = self.vectorizador.buscar_semantica(
            query=query,
            embeddings_base=embeddings,
            textos_base=textos,
            top_k=min(top_k, len(textos))
        )

        # Recuperar índices de resultados
        indices_originales = df_busqueda.index.tolist()
        indices_resultados = [indices_originales[textos.index(r[0])] for r in resultados]

        df_resultados = df_vectorizado.loc[indices_resultados].copy()
        df_resultados["similaridad"] = [r[1] for r in resultados]

        return df_resultados.sort_values("similaridad", ascending=False)

    def generar_reporte_busqueda(
        self,
        query: str,
        df_vectorizado: pd.DataFrame,
        top_k: int = 5
    ) -> str:
        """
        Genera un reporte legible con los resultados de la búsqueda.

        Args:
            query: Consulta de búsqueda
            df_vectorizado: DataFrame vectorizado
            top_k: Resultados a mostrar

        Returns:
            str: Reporte formateado
        """
        resultados = self.buscar_semantica(query, df_vectorizado, top_k=top_k)

        reporte = f"""
╔════════════════════════════════════════════════════════════════╗
║            RESULTADOS DE BÚSQUEDA SEMÁNTICA TALOS              ║
╚════════════════════════════════════════════════════════════════╝

Consulta: "{query}"
Resultados encontrados: {len(resultados)}

"""
        for idx, (_, row) in enumerate(resultados.iterrows(), 1):
            reporte += f"\n[{idx}] {row['tipo']}\n"
            reporte += f"    Similaridad: {row['similaridad']:.4f}\n"
            reporte += f"    {row['texto']}\n"
            if 'producto' in row and pd.notna(row['producto']):
                reporte += f"    Producto: {row['producto']}\n"
                reporte += f"    Categoría: {row['categoria']}\n"
                reporte += f"    Importe: ${row['importe']:.2f}\n"

        return reporte


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


def main(ruta_pdf: str):
    """
    Procesa un reporte PDF de auditoría de inventario.
    
    Args:
        ruta_pdf: Ruta al archivo PDF del reporte
    """
    
    print("\n" + "="*80)
    print("PROCESADOR DE REPORTES DE AUDITORÍA DE INVENTARIO - TALOS")
    print("="*80)
    
    # Verificar que el archivo existe
    if not Path(ruta_pdf).exists():
        print(f"❌ Error: El archivo '{ruta_pdf}' no existe")
        return
    
    # 1. INICIALIZAR PIPELINE
    print("\n[1/3] Inicializando pipeline...")
    pipeline = PipelineAuditoriaCompleto()
    print("      ✓ Pipeline listo")
    
    # 2. PROCESAR PDF
    print("\n[2/3] Procesando PDF del reporte...")
    try:
        datos = pipeline.procesar_reporte_pdf(ruta_pdf)
        print(f"      ✓ Extracción completada")
        print(f"        - {len(datos['kpis'])} KPIs extraídos")
        print(f"        - {len(datos['alertas_faltantes'])} alertas de faltantes")
        print(f"        - {len(datos['alertas_sobrantes'])} alertas de sobrantes")
    except Exception as e:
        print(f"❌ Error al procesar PDF: {e}")
        return
    
    # 3. MOSTRAR SOLO LAS ALERTAS EXISTENTES
    print("\n[3/3] Resultados: alertas encontradas")
    alertas = []
    for alerta in datos.get('alertas_faltantes', []):
        alerta_copy = asdict(alerta)
        alerta_copy['tipo'] = 'FALTANTE'
        alertas.append(alerta_copy)
    for alerta in datos.get('alertas_sobrantes', []):
        alerta_copy = asdict(alerta)
        alerta_copy['tipo'] = 'SOBRANTE'
        alertas.append(alerta_copy)

    if not alertas:
        print("      No se encontraron alertas en el reporte.")
    else:
        grouped = {'FALTANTE': [], 'SOBRANTE': []}
        for alerta in alertas:
            grouped[alerta['tipo']].append(alerta)

        for tipo in ['FALTANTE', 'SOBRANTE']:
            if not grouped[tipo]:
                continue
            print(f"\n      {tipo}s ({len(grouped[tipo])})")
            print("      " + "-" * 50)
            for idx, alerta in enumerate(grouped[tipo], 1):
                producto = alerta.get('producto') or alerta.get('item') or alerta.get('artículo') or 'N/A'
                categoria = alerta.get('categoria', 'N/A')
                importe = alerta.get('importe')
                detalle = alerta.get('detalle') or alerta.get('descripcion') or alerta.get('texto') or ''

                print(f"      [{idx}] Producto: {producto}")
                print(f"           Categoría: {categoria}")
                if importe is not None:
                    try:
                        print(f"           Importe: ${float(importe):.2f}")
                    except (TypeError, ValueError):
                        print(f"           Importe: {importe}")
                if detalle:
                    print(f"           Detalle: {detalle}")

    print("\n" + "="*80)
    print("✓ Sesión finalizada")
    print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ejemplo_uso_auditoria.py <ruta_al_pdf>")
        print("\nEjemplo:")
        print("  python ejemplo_uso_auditoria.py 'Reporte_Auditoría.pdf'")
        sys.exit(1)
    
    ruta_pdf = sys.argv[1]
    main(ruta_pdf)
