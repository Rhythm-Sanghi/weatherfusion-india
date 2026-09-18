import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { AnalyticsPage } from "../pages/AnalyticsPage";
import { EventDetailPage } from "../pages/EventDetailPage";
import { EventsPage } from "../pages/EventsPage";
import { MapPage } from "../pages/MapPage";
import { ReviewQueuePage } from "../pages/ReviewQueuePage";
import { ReviewWorkspacePage } from "../pages/ReviewWorkspacePage";
import { SituationPage } from "../pages/SituationPage";
import { SourcesPage } from "../pages/SourcesPage";
import { SystemPage } from "../pages/SystemPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      {
        path: "/",
        element: <SituationPage />,
      },
      {
        path: "/map",
        element: <MapPage />,
      },
      {
        path: "/events",
        element: <EventsPage />,
      },
      { path: "/events/:eventId", element: <EventDetailPage /> },
      {
        path: "/review",
        element: <ReviewQueuePage />,
      },
      { path: "/review/:eventId", element: <ReviewWorkspacePage /> },
      {
        path: "/analytics",
        element: <AnalyticsPage />,
      },
      {
        path: "/sources",
        element: <SourcesPage />,
      },
      { path: "/system", element: <SystemPage /> },
    ],
  },
]);
