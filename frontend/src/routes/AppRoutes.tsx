import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { AnalyticsPage } from "../pages/AnalyticsPage";
import { ArchitecturePage } from "../pages/ArchitecturePage";
import { CitizenReportPage } from "../pages/CitizenReportPage";
import { EventDetailPage } from "../pages/EventDetailPage";
import { IncidentBriefPage } from "../pages/IncidentBriefPage";
import { LiveFeedPage } from "../pages/LiveFeedPage";
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
      { path: "/reports/citizen", element: <CitizenReportPage /> },
      { path: "/live-feed", element: <LiveFeedPage /> },
      { path: "/events/:eventId", element: <EventDetailPage /> },
      { path: "/events/:eventId/brief", element: <IncidentBriefPage /> },
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
      { path: "/architecture", element: <ArchitecturePage /> },
    ],
  },
]);
