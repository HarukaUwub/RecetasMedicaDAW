import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import MainLayout from "./layout/MainLayout";

import Login from "./pages/Login";
import Pacientes from "./pages/Pacientes";
import Medicos from "./pages/Medicos";
import RecetaForm from "./pages/RecetaForm";
import RecetasList from "./pages/RecetasList";
import LocalRecetas from "./pages/LocalRecetas";

function PrivateRoute({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsAuthenticated(!!token);
  }, []);

  if (isAuthenticated === null) {
    return <div>Cargando...</div>;
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <MainLayout>
                <Navigate to="/recetas" replace />
              </MainLayout>
            </PrivateRoute>
          }
        />
        <Route
          path="/pacientes"
          element={
            <PrivateRoute>
              <MainLayout>
                <Pacientes />
              </MainLayout>
            </PrivateRoute>
          }
        />
        <Route
          path="/medicos"
          element={
            <PrivateRoute>
              <MainLayout>
                <Medicos />
              </MainLayout>
            </PrivateRoute>
          }
        />
        <Route
          path="/recetas"
          element={
            <PrivateRoute>
              <MainLayout>
                <RecetaForm />
              </MainLayout>
            </PrivateRoute>
          }
        />
        <Route
          path="/recetas/list"
          element={
            <PrivateRoute>
              <MainLayout>
                <RecetasList />
              </MainLayout>
            </PrivateRoute>
          }
        />
        <Route
          path="/local/recetas"
          element={
            <PrivateRoute>
              <MainLayout>
                <LocalRecetas />
              </MainLayout>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
