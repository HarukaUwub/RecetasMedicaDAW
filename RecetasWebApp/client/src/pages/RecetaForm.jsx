import { useEffect, useState } from "react";
import { TextField, Button, Card, CardContent, Typography, MenuItem } from "@mui/material";
import api from "../api";

export default function RecetaForm() {
  const [pacientes, setPacientes] = useState([]);
  const [medicos, setMedicos] = useState([]);
  
  const [form, setForm] = useState({
    paciente_id: "",
    medico: null,
    diagnostico: "",
    indicaciones: "",
    medicamentos: [
      { nombre: "", dosis: "", frecuencia: "", duracion: "" }
    ]
  });

  useEffect(() => {
    api.get("/pacientes").then(r => setPacientes(r.data));
    api.get("/medicos").then(r => setMedicos(r.data));
  }, []);

  const agregarMedicamento = () => {
    setForm({
      ...form,
      medicamentos: [...form.medicamentos, { nombre:"", dosis:"", frecuencia:"", duracion:"" }]
    });
  };

  const eliminarMedicamento = (index) => {
    const nuevosMedicamentos = form.medicamentos.filter((_, i) => i !== index);
    setForm({ ...form, medicamentos: nuevosMedicamentos });
  };

  const enviar = () => {
    // Validaciones
    if (!form.paciente_id) {
      alert("Seleccione un paciente");
      return;
    }
    if (!form.medico) {
      alert("Seleccione un médico");
      return;
    }
    if (!form.diagnostico.trim()) {
      alert("Ingrese un diagnóstico");
      return;
    }
    if (form.medicamentos.length === 0 || form.medicamentos.some(m => !m.nombre.trim())) {
      alert("Agregue al menos un medicamento con nombre");
      return;
    }

    // Preparar payload
    const payload = {
      paciente_id: form.paciente_id,
      medico: {
        id: form.medico.id,
        nombre: form.medico.nombre,
        cedula: form.medico.cedula,
        correo: form.medico.correo || ""
      },
      diagnostico: form.diagnostico,
      indicaciones: form.indicaciones,
      medicamentos: form.medicamentos.filter(m => m.nombre.trim())
    };

    api.post("/recetas", payload)
      .then(r => {
        let mensaje = "✅ Receta creada exitosamente!\n\n";
        mensaje += `ID de Receta: ${r.data.id_receta}\n`;
        if (r.data.pdf_path) {
          mensaje += "✓ PDF generado correctamente\n";
        }
        mensaje += "✓ XML enviado al Drive";
        alert(mensaje);
        // Limpiar formulario
        setForm({
          paciente_id: "",
          medico: null,
          diagnostico: "",
          indicaciones: "",
          medicamentos: [{ nombre: "", dosis: "", frecuencia: "", duracion: "" }]
        });
      })
      .catch(err => {
        const errorMsg = err.response?.data?.detail || err.message || "Error desconocido";
        alert("Error: " + errorMsg);
      });
  };

  return (
    <div>
      <Typography variant="h4">Nueva Receta</Typography>

      <Card sx={{ mt: 2 }}>
        <CardContent>

          <TextField select fullWidth margin="dense" label="Paciente"
            value={form.paciente_id}
            onChange={e => setForm({ ...form, paciente_id: e.target.value })}
          >
            {pacientes.map(p => (
              <MenuItem key={p.id} value={p.id}>
                {p.nombre} {p.apellido}
              </MenuItem>
            ))}
          </TextField>

          <TextField select fullWidth margin="dense" label="Médico"
            value={form.medico?.id || ""}
            onChange={e => {
              const medicoSeleccionado = medicos.find(m => m.id === e.target.value);
              setForm({ ...form, medico: medicoSeleccionado || null });
            }}
          >
            {medicos.map(m => (
              <MenuItem key={m.id} value={m.id}>
                {m.nombre} — {m.cedula}
              </MenuItem>
            ))}
          </TextField>

          <TextField label="Diagnóstico" fullWidth multiline margin="dense"
            value={form.diagnostico}
            onChange={e => setForm({ ...form, diagnostico: e.target.value })}
          />

          <TextField label="Indicaciones" fullWidth multiline margin="dense"
            value={form.indicaciones}
            onChange={e => setForm({ ...form, indicaciones: e.target.value })}
          />

          <Typography variant="h6" sx={{ mt: 2 }}>Medicamentos</Typography>

          {form.medicamentos.map((m, i) => (
            <Card key={i} sx={{ p:2, mb:1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <Typography variant="subtitle2">Medicamento {i + 1}</Typography>
                {form.medicamentos.length > 1 && (
                  <Button size="small" color="error" onClick={() => eliminarMedicamento(i)}>
                    Eliminar
                  </Button>
                )}
              </div>
              <TextField label="Nombre *" fullWidth margin="dense" required
                value={m.nombre}
                onChange={e => {
                  const meds = [...form.medicamentos];
                  meds[i].nombre = e.target.value;
                  setForm({ ...form, medicamentos: meds });
                }}
              />
              <TextField label="Dosis" fullWidth margin="dense"
                value={m.dosis}
                onChange={e => {
                  const meds = [...form.medicamentos];
                  meds[i].dosis = e.target.value;
                  setForm({ ...form, medicamentos: meds });
                }}
              />
              <TextField label="Frecuencia" fullWidth margin="dense"
                value={m.frecuencia}
                onChange={e => {
                  const meds = [...form.medicamentos];
                  meds[i].frecuencia = e.target.value;
                  setForm({ ...form, medicamentos: meds });
                }}
              />
              <TextField label="Duración" fullWidth margin="dense"
                value={m.duracion}
                onChange={e => {
                  const meds = [...form.medicamentos];
                  meds[i].duracion = e.target.value;
                  setForm({ ...form, medicamentos: meds });
                }}
              />
            </Card>
          ))}

          <Button onClick={agregarMedicamento} sx={{ mt:1 }}>
            + Agregar medicamento
          </Button>

          <Button variant="contained" onClick={enviar} sx={{ mt: 2 }}>
            Enviar Receta
          </Button>

        </CardContent>
      </Card>
    </div>
  );
}
