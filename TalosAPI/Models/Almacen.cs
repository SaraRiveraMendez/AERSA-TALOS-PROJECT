using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Almacen
{
    public int Idalmacen { get; set; }

    public int Idsucursal { get; set; }

    public string AlmacenNombre { get; set; } = null!;

    public string? AlmacenEncargado { get; set; }

    public bool AlmacenEstatus { get; set; }

    public bool AlmacenOculto { get; set; }

    public string? AlmacenUsuarios { get; set; }

    public int? AlmaenOculto { get; set; }

    public DateOnly? AlmacenFechacreacion { get; set; }

    public virtual ICollection<Inventariome> Inventariomes { get; set; } = new List<Inventariome>();
}
