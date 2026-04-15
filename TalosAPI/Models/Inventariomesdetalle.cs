using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Inventariomesdetalle
{
    public int Idinventariomesdetalle { get; set; }

    public int Idinventariomes { get; set; }

    public int Idproducto { get; set; }

    public decimal InventariomesdetalleStockinicial { get; set; }

    public decimal InventariomesdetalleStockteorico { get; set; }

    /// <summary>
    /// este campo contiene las cantidades después de explosionar una receta\n\n
    /// </summary>
    public decimal InventariomesdetalleExplosion { get; set; }

    public decimal? InventariomesdetalleStockfisico { get; set; }

    /// <summary>
    /// es un campo automático, es la sumatoria de stock fisico y explosion.\n\ncampo deshabilitado para edición\n\nal momento de cambiar el input de stock fisico, este campo se debe de actualizar
    /// </summary>
    public decimal InventariomesdetalleTotalfisico { get; set; }

    /// <summary>
    /// diferencia entre el stock teorico y el fisico
    /// </summary>
    public decimal? InventariomesdetalleDiferencia { get; set; }

    /// <summary>
    /// por defecto, se pone como no revisada.
    /// Si el registro se pone como revisado, ya no se podrá modificar la existencia. 
    /// </summary>
    public bool InventariomesdetalleRevisada { get; set; }

    public decimal InventariomesdetalleIngresocompra { get; set; }

    public decimal InventariomesdetalleIngresorequisicion { get; set; }

    public decimal InventariomesdetalleEgresorequisicion { get; set; }

    public decimal InventariomesdetalleEgresoventa { get; set; }

    /// <summary>
    /// campo para setear los reajustes del producto.
    /// </summary>
    public decimal InventariomesdetalleReajuste { get; set; }

    public decimal InventariomesdetalleIngresoordentablajeria { get; set; }

    public decimal? InventariomesdetalleEgresoordentablajeria { get; set; }

    public decimal? InventariomesdetalleEgresodevolucion { get; set; }

    public decimal? InventariomesdetalleCostopromedio { get; set; }

    /// <summary>
    /// multiplicacion de la diferencia por el costo promedio
    /// </summary>
    public decimal? InventariomesdetalleDifimporte { get; set; }

    /// <summary>
    /// multiplicacion del stock fisico por el costo promedio
    /// </summary>
    public decimal? InventariomesdetalleImportefisico { get; set; }

    public string? InventariomesdetalleAclaracion { get; set; }

    public string? InventariomesdetalleCategoriaAclaracion { get; set; }

    public virtual Inventariome IdinventariomesNavigation { get; set; } = null!;

    public virtual Producto IdproductoNavigation { get; set; } = null!;
}
