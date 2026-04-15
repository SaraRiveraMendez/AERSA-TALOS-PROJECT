using System;
using System.Collections.Generic;

namespace TalosAPI.Models;

public partial class Unidadmedidum
{
    public int Idunidadmedida { get; set; }

    public string UnidadmedidaNombre { get; set; } = null!;

    public string UnidadmedidaEsMx { get; set; } = null!;

    public string UnidadmedidaEnUs { get; set; } = null!;

    public virtual ICollection<Producto> Productos { get; set; } = new List<Producto>();

    public virtual ICollection<Productotalo> Productotalos { get; set; } = new List<Productotalo>();
}
