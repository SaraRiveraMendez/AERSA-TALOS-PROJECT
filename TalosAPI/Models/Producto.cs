using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Producto
{
    public int Idproducto { get; set; }

    public string? IdAersa { get; set; }

    public int Idempresa { get; set; }

    public int Idunidadmedida { get; set; }

    public uint? Idimpuesto { get; set; }

    public string ProductoNombre { get; set; } = null!;

    public int? Idcategoria { get; set; }

    public int? Idsubcategoria { get; set; }

    /// <summary>
    /// sólo aplica cuando es de la categoría bebidas, 
    /// </summary>
    public decimal ProductoRendimiento { get; set; }

    public decimal? ProductoUltimocosto { get; set; }

    public bool ProductoBaja { get; set; }

    public string ProductoTipo { get; set; } = null!;

    public decimal? ProductoCosto { get; set; }

    public bool? ProductoIva { get; set; }

    public decimal? ProductoPrecio { get; set; }

    public decimal? ProductoRendimientooriginal { get; set; }

    public decimal? ProductoIeps { get; set; }

    public sbyte ProductoOculto { get; set; }

    public decimal? ProductoPreciofranquicia { get; set; }

    public string? ProductoComentarioreceta { get; set; }

    public string? DivisionClave { get; set; }

    public string? GrupoClave { get; set; }

    public string? ClaseClave { get; set; }

    public string? SubclaseClave { get; set; }

    public double? ProductoCostomaximo { get; set; }

    public sbyte ProductoDisponiblemarket { get; set; }

    public string? ProductoDescripcion { get; set; }

    public int? Idproductotalos { get; set; }

    public sbyte? ProductotalosValidado { get; set; }

    public string? ImagePath { get; set; }

    public DateTime? CreatedAt { get; set; }

    public virtual Categorium? IdcategoriaNavigation { get; set; }

    public virtual Categorium? IdsubcategoriaNavigation { get; set; }

    public virtual Unidadmedidum IdunidadmedidaNavigation { get; set; } = null!;

    public virtual ICollection<Inventariomesdetalle> Inventariomesdetalles { get; set; } = new List<Inventariomesdetalle>();
}
