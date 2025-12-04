import { useEffect, useState } from "react";
import { TextField, Button, Card, CardContent, Typography, MenuItem } from "@mui/material";
import api from "../api";

function Pacientes() {
  const [data, setData] = useState([]);
  const [form, setForm] = useState({
    id: "",
    nombre: "",
    apellido: "",
    fecha_nacimiento: "",
    sexo: "",
    telefono: "",
    correo: "",
  });

  const cargar = () => {
    api.get("/pacientes").then((r) => setData(r.data));
  };

  useEffect(() => {
    cargar();
  }, []);

  const enviar = () => {
    if (!form.id || !form.nombre || !form.apellido) {
      alert("Complete los campos obligatorios: ID, Nombre y Apellido");
      return;
    }
    api.post("/pacientes", form).then(() => {
      cargar();
      setForm({ id: "", nombre: "", apellido: "", fecha_nacimiento: "", sexo: "", telefono: "", correo: "" });
      alert("Paciente creado exitosamente");
    }).catch((err) => {
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error: " + errorMsg);
    });
  };

  // ✅ USAR EL CLIENTE API (axios) EN LUGAR DE FETCH
  const exportPatients = async () => {
    try {
      const res = await api.post("/pacientes/export-xsd");
      alert(`Exportación completada:\n${JSON.stringify(res.data.result, null, 2)}`);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error exportando pacientes: " + errorMsg);
    }
  };

  const importPatients = async () => {
    try {
      const res = await api.post("/pacientes/import-xsd");
      alert(`Importación completada:\n${JSON.stringify(res.data.result, null, 2)}`);
      cargar(); // Recargar lista
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error importando pacientes: " + errorMsg);
    }
  };

  return (
    <div>
      <Typography variant="h4">Gestión de Pacientes</Typography>

      <Card sx={{ mb: 3, mt: 2 }}>
        <CardContent>
          <TextField label="ID *" fullWidth margin="dense" required
            value={form.id} onChange={e => setForm({ ...form, id: e.target.value })}
          />
          <TextField label="Nombre *" fullWidth margin="dense" required
            value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })}
          />
          <TextField label="Apellido *" fullWidth margin="dense" required
            value={form.apellido} onChange={e => setForm({ ...form, apellido: e.target.value })}
          />
          <TextField label="Fecha de Nacimiento" fullWidth margin="dense" type="date"
            InputLabelProps={{ shrink: true }}
            value={form.fecha_nacimiento} onChange={e => setForm({ ...form, fecha_nacimiento: e.target.value })}
          />
          <TextField select label="Sexo" fullWidth margin="dense"
            value={form.sexo} onChange={e => setForm({ ...form, sexo: e.target.value })}
          >
            <MenuItem value="">Seleccione...</MenuItem>
            <MenuItem value="M">Masculino</MenuItem>
            <MenuItem value="F">Femenino</MenuItem>
            <MenuItem value="O">Otro</MenuItem>
          </TextField>
          <TextField label="Teléfono" fullWidth margin="dense"
            value={form.telefono} onChange={e => setForm({ ...form, telefono: e.target.value })}
          />
          <TextField label="Correo" fullWidth margin="dense"
            value={form.correo} onChange={e => setForm({ ...form, correo: e.target.value })}
          />

          <Button variant="contained" onClick={enviar} sx={{ mt: 2 }}>
            Guardar
          </Button>
        </CardContent>
      </Card>

      <Typography variant="h5">Listado</Typography>
      {data.map(p => (
        <Card key={p.id} sx={{ mb: 1 }}>
          <CardContent>
            <Typography variant="body1"><strong>ID:</strong> {p.id}</Typography>
            <Typography variant="body1"><strong>Nombre:</strong> {p.nombre} {p.apellido}</Typography>
            {p.fecha_nacimiento && <Typography variant="body2">Fecha Nacimiento: {p.fecha_nacimiento}</Typography>}
            {p.sexo && <Typography variant="body2">Sexo: {p.sexo}</Typography>}
            {p.telefono && <Typography variant="body2">Teléfono: {p.telefono}</Typography>}
            {p.correo && <Typography variant="body2">Correo: {p.correo}</Typography>}
          </CardContent>
        </Card>
      ))}

      <div style={{ marginTop: 16, display: "flex", gap: "8px" }}>
        <Button variant="contained" color="success" onClick={exportPatients}>
          Exportar pacientes (XSD / Drive)
        </Button>
        <Button variant="contained" color="info" onClick={importPatients}>
          Importar pacientes (carpeta local)
        </Button>
      </div>
    </div>
  );
}

export default Pacientes;
