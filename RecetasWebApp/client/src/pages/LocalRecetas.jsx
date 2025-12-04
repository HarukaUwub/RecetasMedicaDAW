import { useState, useEffect } from "react";
import {
  Card, CardContent, Typography, Button, Box, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, Dialog,
  DialogTitle, DialogContent, DialogActions
} from "@mui/material";
import api from "../api";

export default function LocalRecetas() {
  const [recetas, setRecetas] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [filtroOrigen, setFiltroOrigen] = useState(null);
  const [selectedReceta, setSelectedReceta] = useState(null);
  const [openDetails, setOpenDetails] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);

  const cargar = async (origen = null) => {
    setLoading(true);
    try {
      const params = origen ? `?filtro_origen=${origen}` : "";
      const res = await api.get(`/local-admin/recetas-locales${params}`);
      setRecetas(res.data);
      setFiltroOrigen(origen);
      loadStats();
    } catch (err) {
      console.error("Error cargando recetas:", err);
      alert("Error: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const res = await api.get("/local-admin/stats");
      setStats(res.data);
    } catch (err) {
      console.error("Error cargando stats:", err);
    }
  };

  // ✅ FORZAR SINCRONIZACIÓN
  const forzarSincronizacion = async () => {
    if (!window.confirm("¿Forzar sincronización con Drive?")) return;
    
    setSincronizando(true);
    try {
      const res = await api.post("/local-admin/forzar-sincronizacion");
      alert(`Sincronización completada:\n${JSON.stringify(res.data, null, 2)}`);
      // Recargar después de sincronizar
      setTimeout(() => cargar(filtroOrigen), 2000);
    } catch (err) {
      alert("Error sincronizando: " + (err.response?.data?.detail || err.message));
    } finally {
      setSincronizando(false);
    }
  };

  useEffect(() => {
    cargar();
  }, []);

  const descargarPDF = async (id_receta) => {
    try {
      const res = await api.get(`/local-admin/recetas-locales/${id_receta}/pdf`, {
        responseType: "blob"
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `receta_${id_receta}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert("Error descargando PDF: " + (err.response?.data?.detail || err.message));
    }
  };

  const eliminar = async (id_receta) => {
    if (window.confirm("¿Confirma eliminar esta receta?")) {
      try {
        await api.delete(`/local-admin/recetas-locales/${id_receta}`);
        alert("Receta eliminada");
        cargar(filtroOrigen);
      } catch (err) {
        alert("Error: " + (err.response?.data?.detail || err.message));
      }
    }
  };

  const abrirDetalles = (receta) => {
    setSelectedReceta(receta);
    setOpenDetails(true);
  };

  const getOrigenColor = (origen) => {
    const colors = { drive: "primary", local: "success", web: "info" };
    return colors[origen] || "default";
  };

  return (
    <div>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">
          📋 Recetas Locales Procesadas
        </Typography>
        <Button
          variant="contained"
          color="secondary"
          onClick={forzarSincronizacion}
          disabled={sincronizando}
          sx={{ textTransform: "none" }}
        >
          {sincronizando ? "Sincronizando..." : "🔄 Forzar Sincronización"}
        </Button>
      </Box>

      {/* Estadísticas */}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 2, mb: 3 }}>
        <Card>
          <CardContent>
            <Typography color="textSecondary">Total Recetas</Typography>
            <Typography variant="h5">{stats.total || 0}</Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography color="textSecondary">Con PDF</Typography>
            <Typography variant="h5">{stats.con_pdf || 0}</Typography>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography color="textSecondary">Desde Drive</Typography>
            <Typography variant="h5">{stats.por_origen?.drive || 0}</Typography>
          </CardContent>
        </Card>
      </Box>

      {/* Botones de filtro */}
      <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
        <Button variant={filtroOrigen === null ? "contained" : "outlined"} onClick={() => cargar()}>
          Todas
        </Button>
        <Button variant={filtroOrigen === "drive" ? "contained" : "outlined"} onClick={() => cargar("drive")}>
          Desde Drive
        </Button>
        <Button variant={filtroOrigen === "local" ? "contained" : "outlined"} onClick={() => cargar("local")}>
          Locales
        </Button>
      </Box>

      {/* Tabla */}
      <TableContainer component={Card}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: "#f5f5f5" }}>
              <TableCell><b>ID Receta</b></TableCell>
              <TableCell><b>Paciente</b></TableCell>
              <TableCell><b>Médico</b></TableCell>
              <TableCell><b>Origen</b></TableCell>
              <TableCell><b>Fecha</b></TableCell>
              <TableCell><b>PDF</b></TableCell>
              <TableCell><b>Acciones</b></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {recetas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                  No hay recetas
                </TableCell>
              </TableRow>
            ) : (
              recetas.map((r) => (
                <TableRow key={r.id_receta}>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}>
                      {r.id_receta.substring(0, 12)}...
                    </Typography>
                  </TableCell>
                  <TableCell>{r.paciente_id}</TableCell>
                  <TableCell>{r.medico_id}</TableCell>
                  <TableCell>
                    <Chip label={r.origen} color={getOrigenColor(r.origen)} size="small" />
                  </TableCell>
                  <TableCell>{new Date(r.fecha_emision).toLocaleDateString()}</TableCell>
                  <TableCell>
                    {r.pdf_path ? (
                      <Chip label="✓ PDF" color="success" size="small" />
                    ) : (
                      <Chip label="✗ Sin PDF" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => abrirDetalles(r)}
                      >
                        Ver
                      </Button>
                      {r.pdf_path && (
                        <Button
                          size="small"
                          variant="outlined"
                          color="success"
                          onClick={() => descargarPDF(r.id_receta)}
                        >
                          PDF
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => eliminar(r.id_receta)}
                      >
                        Del
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Dialog de detalles */}
      <Dialog open={openDetails} onClose={() => setOpenDetails(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Detalles de Receta</DialogTitle>
        <DialogContent>
          {selectedReceta && (
            <Box sx={{ mt: 2 }}>
              <Typography><b>ID:</b> {selectedReceta.id_receta}</Typography>
              <Typography><b>Paciente:</b> {selectedReceta.paciente_id}</Typography>
              <Typography><b>Médico:</b> {selectedReceta.medico_id}</Typography>
              <Typography><b>Origen:</b> {selectedReceta.origen}</Typography>
              <Typography><b>Fecha:</b> {new Date(selectedReceta.fecha_emision).toLocaleString()}</Typography>
              <Typography sx={{ mt: 2 }}><b>Diagnóstico:</b></Typography>
              <Typography sx={{ whiteSpace: "pre-wrap", backgroundColor: "#f5f5f5", p: 1 }}>
                {selectedReceta.diagnostico}
              </Typography>
              <Typography sx={{ mt: 2 }}><b>Indicaciones:</b></Typography>
              <Typography sx={{ whiteSpace: "pre-wrap", backgroundColor: "#f5f5f5", p: 1 }}>
                {selectedReceta.indicaciones}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDetails(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}



