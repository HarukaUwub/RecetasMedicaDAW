import { useEffect, useState } from "react";
import { TextField, Button, Card, CardContent, Typography } from "@mui/material";
import api from "../api";

export default function Medicos() {
  const [data, setData] = useState([]);
  const [form, setForm] = useState({
    id: "",
    nombre: "",
    cedula: "",
    correo: "",
  });

  const cargar = () => {
    api.get("/medicos").then(r => setData(r.data));
  };

  useEffect(() => {
    cargar();
  }, []);

  const enviar = () => {
    api.post("/medicos", form).then(() => {
      cargar();
      setForm({ id:"", nombre:"", cedula:"", correo:"" });
      alert("Médico creado exitosamente");
    }).catch((err) => {
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error: " + errorMsg);
    });
  };

  // ✅ USAR EL CLIENTE API (axios)
  const exportMedicos = async () => {
    try {
      const res = await api.post("/medicos/export-xsd");
      alert(`Exportación completada:\n${JSON.stringify(res.data.result, null, 2)}`);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error exportando medicos: " + errorMsg);
    }
  };

  const importMedicos = async () => {
    try {
      const res = await api.post("/medicos/import-xsd");
      alert(`Importación completada:\n${JSON.stringify(res.data.result, null, 2)}`);
      cargar(); // Recargar lista
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
      alert("Error importando medicos: " + errorMsg);
    }
  };

  return (
    <div>
      <Typography variant="h4">Gestión de Médicos</Typography>

      <Card sx={{ mb: 3, mt: 2 }}>
        <CardContent>
          <TextField label="ID" fullWidth margin="dense"
            value={form.id} onChange={e => setForm({ ...form, id: e.target.value })}
          />
          <TextField label="Nombre" fullWidth margin="dense"
            value={form.nombre} onChange={e => setForm({ ...form, nombre: e.target.value })}
          />
          <TextField label="Cédula" fullWidth margin="dense"
            value={form.cedula} onChange={e => setForm({ ...form, cedula: e.target.value })}
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
            <Typography variant="body1"><strong>Nombre:</strong> {p.nombre}</Typography>
            {p.cedula && <Typography variant="body2">Cédula: {p.cedula}</Typography>}
            {p.correo && <Typography variant="body2">Correo: {p.correo}</Typography>}
          </CardContent>
        </Card>
      ))}

      <div style={{ marginTop: 16, display: "flex", gap: "8px" }}>
        <Button variant="contained" color="success" onClick={exportMedicos}>
          Exportar médicos (XSD / Drive)
        </Button>
        <Button variant="contained" color="info" onClick={importMedicos}>
          Importar médicos (carpeta local)
        </Button>
      </div>
    </div>
  );
}
