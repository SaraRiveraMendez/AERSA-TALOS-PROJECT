using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;

namespace TalosAPI.Models;

public partial class TalosTecmtyContext : DbContext
{
    public TalosTecmtyContext(DbContextOptions<TalosTecmtyContext> options)
        : base(options)
    {
    }

    public virtual DbSet<Almacen> Almacens { get; set; }

    public virtual DbSet<Categorium> Categoria { get; set; }

    public virtual DbSet<Inventariome> Inventariomes { get; set; }

    public virtual DbSet<Inventariomesdetalle> Inventariomesdetalles { get; set; }

    public virtual DbSet<Producto> Productos { get; set; }

    public virtual DbSet<Productotalo> Productotalos { get; set; }

    public virtual DbSet<Unidadmedidum> Unidadmedida { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder
            .UseCollation("utf8mb4_unicode_ci")
            .HasCharSet("utf8mb4");

        modelBuilder.Entity<Almacen>(entity =>
        {
            entity.HasKey(e => e.Idalmacen).HasName("PRIMARY");

            entity
                .ToTable("almacen")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.AlmacenEstatus, "almacen_estatus_idx");

            entity.HasIndex(e => e.AlmacenNombre, "almacen_nombre_idx");

            entity.HasIndex(e => e.Idsucursal, "idsucursal");

            entity.Property(e => e.Idalmacen).HasColumnName("idalmacen");
            entity.Property(e => e.AlmacenEncargado)
                .HasMaxLength(255)
                .HasDefaultValueSql("'x'")
                .HasColumnName("almacen_encargado");
            entity.Property(e => e.AlmacenEstatus).HasColumnName("almacen_estatus");
            entity.Property(e => e.AlmacenFechacreacion).HasColumnName("almacen_fechacreacion");
            entity.Property(e => e.AlmacenNombre).HasColumnName("almacen_nombre");
            entity.Property(e => e.AlmacenOculto).HasColumnName("almacen_oculto");
            entity.Property(e => e.AlmacenUsuarios)
                .HasColumnType("text")
                .HasColumnName("almacen_usuarios");
            entity.Property(e => e.AlmaenOculto)
                .HasDefaultValueSql("'0'")
                .HasColumnName("almaen_oculto");
            entity.Property(e => e.Idsucursal).HasColumnName("idsucursal");
        });

        modelBuilder.Entity<Categorium>(entity =>
        {
            entity.HasKey(e => e.Idcategoria).HasName("PRIMARY");

            entity
                .ToTable("categoria")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.CategoriaAlmacenable, "categoria_almacenable_idx");

            entity.HasIndex(e => e.CategoriaVisiblecierre, "categoria_visiblecierre_idx");

            entity.HasIndex(e => e.Idcategoriapadre, "idcategoriapadre");

            entity.HasIndex(e => e.Idcategoriagrupo, "idx_idcategoriagrupo");

            entity.Property(e => e.Idcategoria).HasColumnName("idcategoria");
            entity.Property(e => e.CategoriaAlmacenable)
                .HasComment("sólo aplica para las subcategorias")
                .HasColumnName("categoria_almacenable");
            entity.Property(e => e.CategoriaNombre)
                .HasMaxLength(255)
                .HasColumnName("categoria_nombre");
            entity.Property(e => e.CategoriaVisiblecierre)
                .HasDefaultValueSql("'1'")
                .HasColumnName("categoria_visiblecierre");
            entity.Property(e => e.Idcategoriagrupo).HasColumnName("idcategoriagrupo");
            entity.Property(e => e.Idcategoriapadre).HasColumnName("idcategoriapadre");

            entity.HasOne(d => d.IdcategoriapadreNavigation).WithMany(p => p.InverseIdcategoriapadreNavigation)
                .HasForeignKey(d => d.Idcategoriapadre)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("idcategoriapadre_categoria");
        });

        modelBuilder.Entity<Inventariome>(entity =>
        {
            entity.HasKey(e => e.Idinventariomes).HasName("PRIMARY");

            entity
                .ToTable("inventariomes")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.Idalmacen, "idalmacen");

            entity.HasIndex(e => e.Idauditor, "idauditor");

            entity.HasIndex(e => e.Idempresa, "idempresa");

            entity.HasIndex(e => e.Idpadre, "idpadre");

            entity.HasIndex(e => e.Idsucursal, "idsucursal");

            entity.HasIndex(e => e.Idusuario, "idusuario");

            entity.HasIndex(e => new { e.Idempresa, e.Idsucursal, e.InventariomesFecha }, "idx_inventariomes_emp_suc_fec");

            entity.HasIndex(e => e.InventariomesEstatus, "inventariomes_estatus");

            entity.HasIndex(e => e.InventariomesFecha, "inventariomes_fecha");

            entity.Property(e => e.Idinventariomes).HasColumnName("idinventariomes");
            entity.Property(e => e.Idalmacen).HasColumnName("idalmacen");
            entity.Property(e => e.Idauditor)
                .HasComment("empleado de aersa quien revisará el registro\n")
                .HasColumnName("idauditor");
            entity.Property(e => e.Idempresa).HasColumnName("idempresa");
            entity.Property(e => e.Idpadre).HasColumnName("idpadre");
            entity.Property(e => e.Idsucursal).HasColumnName("idsucursal");
            entity.Property(e => e.Idusuario)
                .HasComment("empleado de la empresa quien realizó el registro del inventario\n")
                .HasColumnName("idusuario");
            entity.Property(e => e.InventariomesCreatedat)
                .HasColumnType("datetime")
                .HasColumnName("inventariomes_createdat");
            entity.Property(e => e.InventariomesEstatus)
                .HasDefaultValueSql("'finalizado'")
                .HasColumnType("enum('generando','finalizado','error','editando','aplicado','terminado')")
                .HasColumnName("inventariomes_estatus");
            entity.Property(e => e.InventariomesFaltantes)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de la columna inventariomesdetalle cuando es negativo")
                .HasColumnName("inventariomes_faltantes");
            entity.Property(e => e.InventariomesFecha)
                .HasColumnType("datetime")
                .HasColumnName("inventariomes_fecha");
            entity.Property(e => e.InventariomesFinalalimentos)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de todos los elementos de inventariomesdetalle_importefisico de los productos de la categoria alimentos")
                .HasColumnName("inventariomes_finalalimentos");
            entity.Property(e => e.InventariomesFinalbebidas)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de todos los elementos de inventariomesdetalle_importefisico de los productos de la categoria bebidas")
                .HasColumnName("inventariomes_finalbebidas");
            entity.Property(e => e.InventariomesFinalmiscelaneos)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("inventariomes_finalmiscelaneos");
            entity.Property(e => e.InventariomesPdf)
                .HasColumnType("text")
                .HasColumnName("inventariomes_pdf");
            entity.Property(e => e.InventariomesPdfInicial)
                .HasColumnType("text")
                .HasColumnName("inventariomes_pdf_inicial");
            entity.Property(e => e.InventariomesRevisada)
                .HasComment("por defecto, el registro se pone como no revisado. \nsi se define como revisada, ya no se podrán modificar los registros del inventario")
                .HasColumnName("inventariomes_revisada");
            entity.Property(e => e.InventariomesSobrantes)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de la columna inventariomesdetalle cuando es mayor que 0")
                .HasColumnName("inventariomes_sobrantes");
            entity.Property(e => e.InventariomesTotal)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de faltantes y sobrantes")
                .HasColumnName("inventariomes_total");
            entity.Property(e => e.InventariomesTotalimportefisico)
                .HasPrecision(15, 2)
                .HasComment("sumatoria de inventariomesdetalle_importefisico\\n\\n")
                .HasColumnName("inventariomes_totalimportefisico");
            entity.Property(e => e.InventariomesUpdatedat)
                .HasColumnType("datetime")
                .HasColumnName("inventariomes_updatedat");
            entity.Property(e => e.InventariomesVersion)
                .HasDefaultValueSql("'1'")
                .HasColumnName("inventariomes_version");
            entity.Property(e => e.InventariomesXls)
                .HasColumnType("text")
                .HasColumnName("inventariomes_xls");
            entity.Property(e => e.InventariomesXlsInicial)
                .HasColumnType("text")
                .HasColumnName("inventariomes_xls_inicial");

            entity.HasOne(d => d.IdalmacenNavigation).WithMany(p => p.Inventariomes)
                .HasForeignKey(d => d.Idalmacen)
                .HasConstraintName("idalmacen_inventariomes");

            entity.HasOne(d => d.IdpadreNavigation).WithMany(p => p.InverseIdpadreNavigation)
                .HasForeignKey(d => d.Idpadre)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("idpadre_inventariomes");
        });

        modelBuilder.Entity<Inventariomesdetalle>(entity =>
        {
            entity.HasKey(e => e.Idinventariomesdetalle).HasName("PRIMARY");

            entity
                .ToTable("inventariomesdetalle")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.Idinventariomes, "idinventariomes");

            entity.HasIndex(e => e.Idproducto, "idproducto_inventariomesdetalle");

            entity.HasIndex(e => new { e.Idinventariomes, e.Idproducto }, "idx_inventariomesdet_inv_pro");

            entity.Property(e => e.Idinventariomesdetalle).HasColumnName("idinventariomesdetalle");
            entity.Property(e => e.Idinventariomes).HasColumnName("idinventariomes");
            entity.Property(e => e.Idproducto).HasColumnName("idproducto");
            entity.Property(e => e.InventariomesdetalleAclaracion)
                .HasColumnType("text")
                .HasColumnName("inventariomesdetalle_aclaracion");
            entity.Property(e => e.InventariomesdetalleCategoriaAclaracion)
                .HasMaxLength(255)
                .HasColumnName("inventariomesdetalle_categoria_aclaracion");
            entity.Property(e => e.InventariomesdetalleCostopromedio)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("inventariomesdetalle_costopromedio");
            entity.Property(e => e.InventariomesdetalleDiferencia)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasComment("diferencia entre el stock teorico y el fisico")
                .HasColumnName("inventariomesdetalle_diferencia");
            entity.Property(e => e.InventariomesdetalleDifimporte)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasComment("multiplicacion de la diferencia por el costo promedio")
                .HasColumnName("inventariomesdetalle_difimporte");
            entity.Property(e => e.InventariomesdetalleEgresodevolucion)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasColumnName("inventariomesdetalle_egresodevolucion");
            entity.Property(e => e.InventariomesdetalleEgresoordentablajeria)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasColumnName("inventariomesdetalle_egresoordentablajeria");
            entity.Property(e => e.InventariomesdetalleEgresorequisicion)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_egresorequisicion");
            entity.Property(e => e.InventariomesdetalleEgresoventa)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_egresoventa");
            entity.Property(e => e.InventariomesdetalleExplosion)
                .HasPrecision(15, 6)
                .HasComment("este campo contiene las cantidades después de explosionar una receta\\n\\n")
                .HasColumnName("inventariomesdetalle_explosion");
            entity.Property(e => e.InventariomesdetalleImportefisico)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasComment("multiplicacion del stock fisico por el costo promedio")
                .HasColumnName("inventariomesdetalle_importefisico");
            entity.Property(e => e.InventariomesdetalleIngresocompra)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_ingresocompra");
            entity.Property(e => e.InventariomesdetalleIngresoordentablajeria)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_ingresoordentablajeria");
            entity.Property(e => e.InventariomesdetalleIngresorequisicion)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_ingresorequisicion");
            entity.Property(e => e.InventariomesdetalleReajuste)
                .HasPrecision(15, 6)
                .HasComment("campo para setear los reajustes del producto.")
                .HasColumnName("inventariomesdetalle_reajuste");
            entity.Property(e => e.InventariomesdetalleRevisada)
                .HasComment("por defecto, se pone como no revisada.\nSi el registro se pone como revisado, ya no se podrá modificar la existencia. ")
                .HasColumnName("inventariomesdetalle_revisada");
            entity.Property(e => e.InventariomesdetalleStockfisico)
                .HasPrecision(15, 3)
                .HasDefaultValueSql("'0.000'")
                .HasColumnName("inventariomesdetalle_stockfisico");
            entity.Property(e => e.InventariomesdetalleStockinicial)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_stockinicial");
            entity.Property(e => e.InventariomesdetalleStockteorico)
                .HasPrecision(15, 6)
                .HasColumnName("inventariomesdetalle_stockteorico");
            entity.Property(e => e.InventariomesdetalleTotalfisico)
                .HasPrecision(15, 6)
                .HasComment("es un campo automático, es la sumatoria de stock fisico y explosion.\\n\\ncampo deshabilitado para edición\\n\\nal momento de cambiar el input de stock fisico, este campo se debe de actualizar")
                .HasColumnName("inventariomesdetalle_totalfisico");

            entity.HasOne(d => d.IdinventariomesNavigation).WithMany(p => p.Inventariomesdetalles)
                .HasForeignKey(d => d.Idinventariomes)
                .HasConstraintName("idinventariomes_inventariomesdetalle");

            entity.HasOne(d => d.IdproductoNavigation).WithMany(p => p.Inventariomesdetalles)
                .HasForeignKey(d => d.Idproducto)
                .HasConstraintName("idproducto_inventariomesdetalle");
        });

        modelBuilder.Entity<Producto>(entity =>
        {
            entity.HasKey(e => e.Idproducto).HasName("PRIMARY");

            entity
                .ToTable("producto")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.Idcategoria, "idcategoria");

            entity.HasIndex(e => e.Idempresa, "idempresa");

            entity.HasIndex(e => e.Idimpuesto, "idimpuesto");

            entity.HasIndex(e => e.Idproductotalos, "idproductotalos");

            entity.HasIndex(e => e.Idsubcategoria, "idsubcategoria");

            entity.HasIndex(e => e.Idunidadmedida, "idunidadmedida");

            entity.HasIndex(e => e.ProductoBaja, "producto_baja_idx");

            entity.HasIndex(e => e.ProductoNombre, "producto_nombre_idx");

            entity.HasIndex(e => e.ProductoOculto, "producto_oculto_idx");

            entity.HasIndex(e => e.ProductoTipo, "producto_tipo_idx");

            entity.Property(e => e.Idproducto).HasColumnName("idproducto");
            entity.Property(e => e.ClaseClave)
                .HasMaxLength(255)
                .HasColumnName("clase_clave");
            entity.Property(e => e.CreatedAt)
                .HasColumnType("datetime")
                .HasColumnName("created_at");
            entity.Property(e => e.DivisionClave)
                .HasMaxLength(255)
                .HasColumnName("division_clave");
            entity.Property(e => e.GrupoClave)
                .HasMaxLength(255)
                .HasColumnName("grupo_clave");
            entity.Property(e => e.IdAersa)
                .HasMaxLength(255)
                .HasColumnName("id_aersa");
            entity.Property(e => e.Idcategoria).HasColumnName("idcategoria");
            entity.Property(e => e.Idempresa).HasColumnName("idempresa");
            entity.Property(e => e.Idimpuesto).HasColumnName("idimpuesto");
            entity.Property(e => e.Idproductotalos).HasColumnName("idproductotalos");
            entity.Property(e => e.Idsubcategoria).HasColumnName("idsubcategoria");
            entity.Property(e => e.Idunidadmedida).HasColumnName("idunidadmedida");
            entity.Property(e => e.ImagePath)
                .HasMaxLength(255)
                .HasColumnName("image_path");
            entity.Property(e => e.ProductoBaja).HasColumnName("producto_baja");
            entity.Property(e => e.ProductoComentarioreceta)
                .HasColumnType("text")
                .HasColumnName("producto_comentarioreceta");
            entity.Property(e => e.ProductoCosto)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("producto_costo");
            entity.Property(e => e.ProductoCostomaximo)
                .HasColumnType("double(15,2)")
                .HasColumnName("producto_costomaximo");
            entity.Property(e => e.ProductoDescripcion)
                .HasMaxLength(255)
                .HasColumnName("producto_descripcion");
            entity.Property(e => e.ProductoDisponiblemarket).HasColumnName("producto_disponiblemarket");
            entity.Property(e => e.ProductoIeps)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("producto_ieps");
            entity.Property(e => e.ProductoIva)
                .HasDefaultValueSql("'0'")
                .HasColumnName("producto_iva");
            entity.Property(e => e.ProductoNombre).HasColumnName("producto_nombre");
            entity.Property(e => e.ProductoOculto).HasColumnName("producto_oculto");
            entity.Property(e => e.ProductoPrecio)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("producto_precio");
            entity.Property(e => e.ProductoPreciofranquicia)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("producto_preciofranquicia");
            entity.Property(e => e.ProductoRendimiento)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'1.000000'")
                .HasComment("sólo aplica cuando es de la categoría bebidas, ")
                .HasColumnName("producto_rendimiento");
            entity.Property(e => e.ProductoRendimientooriginal)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasColumnName("producto_rendimientooriginal");
            entity.Property(e => e.ProductoTipo)
                .HasColumnType("enum('simple','subreceta','plu')")
                .HasColumnName("producto_tipo");
            entity.Property(e => e.ProductoUltimocosto)
                .HasPrecision(15, 2)
                .HasDefaultValueSql("'0.00'")
                .HasColumnName("producto_ultimocosto");
            entity.Property(e => e.ProductotalosValidado)
                .HasDefaultValueSql("'0'")
                .HasColumnName("productotalos_validado");
            entity.Property(e => e.SubclaseClave)
                .HasMaxLength(255)
                .HasColumnName("subclase_clave");

            entity.HasOne(d => d.IdcategoriaNavigation).WithMany(p => p.ProductoIdcategoriaNavigations)
                .HasForeignKey(d => d.Idcategoria)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("idcategoria_producto");

            entity.HasOne(d => d.IdsubcategoriaNavigation).WithMany(p => p.ProductoIdsubcategoriaNavigations)
                .HasForeignKey(d => d.Idsubcategoria)
                .OnDelete(DeleteBehavior.Cascade)
                .HasConstraintName("idsubcategoria_producto");

            entity.HasOne(d => d.IdunidadmedidaNavigation).WithMany(p => p.Productos)
                .HasForeignKey(d => d.Idunidadmedida)
                .HasConstraintName("idunidadmedida_producto");
        });

        modelBuilder.Entity<Productotalo>(entity =>
        {
            entity.HasKey(e => e.Idproductotalos).HasName("PRIMARY");

            entity
                .ToTable("productotalos")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.Idcategoria, "idcategoria");

            entity.HasIndex(e => e.Idsubcategoria, "idsubcategoria");

            entity.HasIndex(e => e.Idunidadmedida, "idunidadmedida");

            entity.HasIndex(e => e.ProductoValidado, "producto_validado_idx");

            entity.Property(e => e.Idproductotalos).HasColumnName("idproductotalos");
            entity.Property(e => e.ClaseClave)
                .HasMaxLength(255)
                .HasColumnName("clase_clave");
            entity.Property(e => e.DivisionClave)
                .HasMaxLength(255)
                .HasColumnName("division_clave");
            entity.Property(e => e.GrupoClave)
                .HasMaxLength(255)
                .HasColumnName("grupo_clave");
            entity.Property(e => e.Idcategoria).HasColumnName("idcategoria");
            entity.Property(e => e.Idsubcategoria).HasColumnName("idsubcategoria");
            entity.Property(e => e.Idunidadmedida).HasColumnName("idunidadmedida");
            entity.Property(e => e.ProductoNombre)
                .HasColumnType("text")
                .HasColumnName("producto_nombre");
            entity.Property(e => e.ProductoRendimiento)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasComment("sólo aplica cuando es de la categoría bebidas, ")
                .HasColumnName("producto_rendimiento");
            entity.Property(e => e.ProductoRendimientooriginal)
                .HasPrecision(15, 6)
                .HasDefaultValueSql("'0.000000'")
                .HasColumnName("producto_rendimientooriginal");
            entity.Property(e => e.ProductoValidado)
                .HasDefaultValueSql("'0'")
                .HasColumnName("producto_validado");
            entity.Property(e => e.ProductoVisible)
                .HasDefaultValueSql("'0'")
                .HasColumnName("producto_visible");
            entity.Property(e => e.SubclaseClave)
                .HasMaxLength(255)
                .HasColumnName("subclase_clave");
            entity.Property(e => e.Total)
                .HasDefaultValueSql("'0'")
                .HasColumnName("total");

            entity.HasOne(d => d.IdcategoriaNavigation).WithMany(p => p.ProductotaloIdcategoriaNavigations)
                .HasForeignKey(d => d.Idcategoria)
                .HasConstraintName("idcategoria_productotalos");

            entity.HasOne(d => d.IdsubcategoriaNavigation).WithMany(p => p.ProductotaloIdsubcategoriaNavigations)
                .HasForeignKey(d => d.Idsubcategoria)
                .HasConstraintName("idsubcategoria_productotalos");

            entity.HasOne(d => d.IdunidadmedidaNavigation).WithMany(p => p.Productotalos)
                .HasForeignKey(d => d.Idunidadmedida)
                .OnDelete(DeleteBehavior.ClientSetNull)
                .HasConstraintName("idunidadmedida_productotalos");
        });

        modelBuilder.Entity<Unidadmedidum>(entity =>
        {
            entity.HasKey(e => e.Idunidadmedida).HasName("PRIMARY");

            entity
                .ToTable("unidadmedida")
                .HasCharSet("utf8mb3")
                .UseCollation("utf8mb3_general_ci");

            entity.HasIndex(e => e.UnidadmedidaEnUs, "unidadmedida_en_US_idx");

            entity.HasIndex(e => e.UnidadmedidaNombre, "unidadmedida_nombre_idx");

            entity.Property(e => e.Idunidadmedida).HasColumnName("idunidadmedida");
            entity.Property(e => e.UnidadmedidaEnUs)
                .HasDefaultValueSql("''")
                .HasColumnName("unidadmedida_en_US");
            entity.Property(e => e.UnidadmedidaEsMx)
                .HasMaxLength(255)
                .HasDefaultValueSql("''")
                .HasColumnName("unidadmedida_es_MX");
            entity.Property(e => e.UnidadmedidaNombre).HasColumnName("unidadmedida_nombre");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
