import { useEffect, useState } from "react";
import { Card, CardContent, Typography, Chip, Box, Button, Stack } from "@mui/material";
import api from "../api";

const verPDF = async (id_receta, tipo = "web") => {
  try {
    const endpoint = tipo === "web" 
      ? `/recetas/${id_receta}/pdf`
      : `/local/recetas/${id_receta}/pdf`;
    
    const response = await api.get(endpoint, {
      responseType: 'blob',
    });
    
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert("Error al abrir el PDF: " + (error.response?.data?.detail || error.message));
  }
};
const reintentarSubida = async () => {
  try {
    const res = await api.post("/recetas/reintentar");
    alert("Reintento completado. Revisa los resultados.");
  } catch (error) {
    console.error("Error reintentando:", error);
    alert("Error al reintentar: " + (error.response?.data?.detail || error.message));
  }
};

const reenviarCorreo = async (idReceta) => {
  try {
    const response = await api.post(`/recetas/${idReceta}/reenviar-correo`);

    alert("Correo reenviado exitosamente");
  } catch (error) {
    console.error("Error al reenviar:", error);
    alert("Error al reenviar: " + (error.response?.data?.detail || error.message));
  }
};



export default function RecetasList() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    cargarRecetas();
  }, []);

  const cargarRecetas = () => {
    setLoading(true);
    api.get("/recetas")
      .then(r => {
        setData(r.data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error al cargar recetas:", err);
        setLoading(false);
      });
  };

  if (loading) {
    return <Typography>Cargando recetas...</Typography>;
  }

  return (
    <div>
      <Typography variant="h4" sx={{ mb: 3 }}>Recetas Generadas</Typography>

      {data.length === 0 ? (
        <Card>
          <CardContent>
            <Typography>No hay recetas registradas</Typography>
          </CardContent>
        </Card>
      ) : (
        data.map(r => (
          <Card key={r.id_receta} sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                <Typography variant="h6">Receta #{r.id_receta}</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip 
                    label={r.sent ? "Enviada" : "Pendiente"} 
                    color={r.sent ? "success" : "warning"}
                    size="small"
                  />
                  {r.pdf_path && (
                    <Chip 
                      label="PDF disponible" 
                      color="info"
                      size="small"
                    />
                  )}
                </Box>
              </Box>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Paciente ID:</strong> {r.paciente_id}
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                <strong>Médico ID:</strong> {r.medico_id}
              </Typography>
              
              {r.diagnostico && (
                <Typography variant="body2" sx={{ mb: 1 }}>
                  <strong>Diagnóstico:</strong> {r.diagnostico}
                </Typography>
              )}
              
              {r.medicamentos && r.medicamentos.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>Medicamentos:</Typography>
                  {r.medicamentos.map((m, idx) => (
                    <Typography key={idx} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
                      • {m.nombre} {m.dosis && `- ${m.dosis}`} {m.frecuencia && `(${m.frecuencia})`}
                    </Typography>
                  ))}
                </Box>
              )}
              
              {r.fecha_emision && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                  Fecha de emisión: {new Date(r.fecha_emision).toLocaleString('es-ES')}
                </Typography>
              )}
              
              {r.created_at && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  Creada: {new Date(r.created_at).toLocaleString('es-ES')}
                </Typography>
              )}
              
              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
  {r.pdf_path && (
    <Button
      variant="outlined"
      color="primary"
      onClick={() => verPDF(r.id_receta, "web")}
    >
      Ver PDF
    </Button>
  )}

  {r.sent ? (
    <Button
      variant="outlined"
      color="warning"
      onClick={() => reenviarCorreo(r.id_receta)}
    >
      Reenviar correo
    </Button>
  ) : (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mr: 2 }}>
        No enviado
      </Typography>

      <Button
        variant="contained"
        color="secondary"
        onClick={reintentarSubida}
      >
        Reintentar subir a Drive
      </Button>
    </>
  )}
</Stack>

            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
