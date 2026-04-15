using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Inventariome
{
    public int Idinventariomes { get; set; }

    public int Idempresa { get; set; }

    public int Idsucursal { get; set; }

    public int Idalmacen { get; set; }

    /// <summary>
    /// empleado de la empresa quien realizó el registro del inventario
    /// 
    /// </summary>
    public int Idusuario { get; set; }

    /// <summary>
    /// empleado de aersa quien revisará el registro
    /// 
    /// </summary>
    public int? Idauditor { get; set; }

    public int? Idpadre { get; set; }

    public DateTime InventariomesFecha { get; set; }

    /// <summary>
    /// por defecto, el registro se pone como no revisado. 
    /// si se define como revisada, ya no se podrán modificar los registros del inventario
    /// </summary>
    public bool InventariomesRevisada { get; set; }

    /// <summary>
    /// sumatoria de todos los elementos de inventariomesdetalle_importefisico de los productos de la categoria alimentos
    /// </summary>
    public decimal InventariomesFinalalimentos { get; set; }

    /// <summary>
    /// sumatoria de todos los elementos de inventariomesdetalle_importefisico de los productos de la categoria bebidas
    /// </summary>
    public decimal InventariomesFinalbebidas { get; set; }

    /// <summary>
    /// sumatoria de la columna inventariomesdetalle cuando es negativo
    /// </summary>
    public decimal InventariomesFaltantes { get; set; }

    /// <summary>
    /// sumatoria de la columna inventariomesdetalle cuando es mayor que 0
    /// </summary>
    public decimal InventariomesSobrantes { get; set; }

    /// <summary>
    /// sumatoria de faltantes y sobrantes
    /// </summary>
    public decimal InventariomesTotal { get; set; }

    /// <summary>
    /// sumatoria de inventariomesdetalle_importefisico\n\n
    /// </summary>
    public decimal InventariomesTotalimportefisico { get; set; }

    public string InventariomesEstatus { get; set; } = null!;

    public decimal? InventariomesFinalmiscelaneos { get; set; }

    public string? InventariomesXls { get; set; }

    public string? InventariomesPdf { get; set; }

    public string? InventariomesXlsInicial { get; set; }

    public string? InventariomesPdfInicial { get; set; }

    public int InventariomesVersion { get; set; }

    public DateTime? InventariomesCreatedat { get; set; }

    public DateTime? InventariomesUpdatedat { get; set; }

    public virtual Almacen IdalmacenNavigation { get; set; } = null!;

    public virtual Inventariome? IdpadreNavigation { get; set; }

    public virtual ICollection<Inventariomesdetalle> Inventariomesdetalles { get; set; } = new List<Inventariomesdetalle>();

    public virtual ICollection<Inventariome> InverseIdpadreNavigation { get; set; } = new List<Inventariome>();
}
