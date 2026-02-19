import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { RunProvider } from "./context/RunContext";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RunProvider>
      <App />
    </RunProvider>
  </React.StrictMode>
);
