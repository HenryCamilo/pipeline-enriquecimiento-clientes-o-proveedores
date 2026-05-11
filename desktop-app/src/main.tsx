import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./themes/shared.css";
import "./themes/windows.css";
import "./themes/ubuntu.css";
import "./index.css";
import { PlatformProvider } from "./platform/PlatformProvider";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PlatformProvider>
      <App />
    </PlatformProvider>
  </React.StrictMode>,
);
