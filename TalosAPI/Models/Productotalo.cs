using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Productotalo
{
    public int Idproductotalos { get; set; }

    public string ProductoNombre { get; set; } = null!;

    public int Idunidadmedida { get; set; }

    public int? Idcategoria { get; set; }

    public int? Idsubcategoria { get; set; }

    /// <summary>
    /// sólo aplica cuando es de la categoría bebidas, 
    /// </summary>
    public decimal? ProductoRendimiento { get; set; }

    public decimal? ProductoRendimientooriginal { get; set; }

    public string? DivisionClave { get; set; }

    public string? GrupoClave { get; set; }

    public string? ClaseClave { get; set; }

    public string? SubclaseClave { get; set; }

    public sbyte? ProductoValidado { get; set; }

    public int? Total { get; set; }

    public sbyte? ProductoVisible { get; set; }

    public virtual Categorium? IdcategoriaNavigation { get; set; }

    public virtual Categorium? IdsubcategoriaNavigation { get; set; }

    public virtual Unidadmedidum IdunidadmedidaNavigation { get; set; } = null!;
}
