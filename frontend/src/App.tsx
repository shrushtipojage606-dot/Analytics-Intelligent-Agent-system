import { BrowserRouter, Routes, Route } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import AlertSettingsPage from "./pages/AlertSettingsPage";
import ReportsPage from "./pages/ReportsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/dashboard/:datasetId" element={<DashboardPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/alerts/:datasetId" element={<AlertSettingsPage />} />
        <Route path="/alerts" element={<AlertSettingsPage />} />
      </Routes>
    </BrowserRouter>
  );
}
