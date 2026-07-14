import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import { QueryClientProvider } from "./app/providers/query-client-provider";
import { WorkbenchProvider } from "./app/providers/workbench-provider";
import { ToastProvider } from "./components/ui/toast";
import { router } from "./app/router";
import "./index.css";

const savedTheme = window.localStorage.getItem("theme");
const shouldUseDark = savedTheme === "dark";
document.documentElement.classList.toggle("dark", shouldUseDark);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider>
      <WorkbenchProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </WorkbenchProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
