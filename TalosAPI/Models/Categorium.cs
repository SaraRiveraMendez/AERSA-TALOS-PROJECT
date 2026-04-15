using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Categorium
{
    public int Idcategoria { get; set; }

    public string CategoriaNombre { get; set; } = null!;

    public int? Idcategoriapadre { get; set; }

    /// <summary>
    /// sólo aplica para las subcategorias
    /// </summary>
    public bool? CategoriaAlmacenable { get; set; }

    public sbyte? CategoriaVisiblecierre { get; set; }

    public uint? Idcategoriagrupo { get; set; }

    public virtual Categorium? IdcategoriapadreNavigation { get; set; }

    public virtual ICollection<Categorium> InverseIdcategoriapadreNavigation { get; set; } = new List<Categorium>();

    public virtual ICollection<Producto> ProductoIdcategoriaNavigations { get; set; } = new List<Producto>();

    public virtual ICollection<Producto> ProductoIdsubcategoriaNavigations { get; set; } = new List<Producto>();

    public virtual ICollection<Productotalo> ProductotaloIdcategoriaNavigations { get; set; } = new List<Productotalo>();

    public virtual ICollection<Productotalo> ProductotaloIdsubcategoriaNavigations { get; set; } = new List<Productotalo>();
}
