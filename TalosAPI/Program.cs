using Microsoft.EntityFrameworkCore;
using TalosAPI.Models;

var builder = WebApplication.CreateBuilder(args);

// 🔥 Conexión a MySQL
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");

builder.Services.AddDbContext<TalosTecmtyContext>(options =>
    options.UseMySql(connectionString, ServerVersion.AutoDetect(connectionString)));

// 🔥 Swagger (opcional pero útil)
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// 🔥 Evitar errores de ciclos
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.ReferenceHandler =
            System.Text.Json.Serialization.ReferenceHandler.IgnoreCycles;
    });

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI();

app.UseHttpsRedirection();


// ENDPOINT PRODUCTOS (YA FUNCIONAL)
app.MapGet("/productos", async (TalosTecmtyContext db) =>
{
    return await db.Productos
        .Select(p => new
        {
            p.Idproducto,
            p.ProductoNombre,
            p.ProductoPrecio,
            p.ProductoCosto
        })
        .Take(10)
        .ToListAsync();
});


// PRODUCTO POR ID
app.MapGet("/productos/{id}", async (int id, TalosTecmtyContext db) =>
{
    var producto = await db.Productos
        .Where(p => p.Idproducto == id)
        .Select(p => new
        {
            p.Idproducto,
            p.ProductoNombre,
            p.ProductoPrecio,
            p.ProductoDescripcion
        })
        .FirstOrDefaultAsync();

    return producto is not null ? Results.Ok(producto) : Results.NotFound();
});


// TEST DB
app.MapGet("/test-db", async (TalosTecmtyContext db) =>
{
    return await db.Database.CanConnectAsync();
});

app.Run();