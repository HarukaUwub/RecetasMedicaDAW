import { Link, useNavigate } from "react-router-dom";
import { AppBar, Toolbar, Button, Box } from "@mui/material";

export default function MainLayout({ children }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" component={Link} to="/pacientes">Pacientes</Button>
          <Button color="inherit" component={Link} to="/medicos">Médicos</Button>
          <Button color="inherit" component={Link} to="/recetas">Nueva Receta</Button>
          <Button color="inherit" component={Link} to="/recetas/list">Recetas Enviadas (Web)</Button>
          <Button color="inherit" component={Link} to="/local/recetas">Recetas Locales / PDFs</Button>
          <Box sx={{ flexGrow: 1 }} />
          <Button color="inherit" onClick={handleLogout}>
            Cerrar Sesión
          </Button>
        </Toolbar>
      </AppBar>

      <Box sx={{ padding: 3 }}>
        {children}
      </Box>
    </>
  );
}
