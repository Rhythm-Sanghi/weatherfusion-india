import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { activateDemoScenario, getDemoFeed, getDemoScenarios, ingestControlledSocialFeed } from "../api/client";

export function LiveFeedPage() {
  const queryClient = useQueryClient();
  const feed = useQuery({ queryKey: ["demo-feed"], queryFn: getDemoFeed });
  const scenarios = useQuery({ queryKey: ["demo-scenarios"], queryFn: getDemoScenarios });
  const refresh = () => { void queryClient.invalidateQueries({ queryKey: ["events"] }); void queryClient.invalidateQueries({ queryKey: ["event-summary"] }); void queryClient.invalidateQueries({ queryKey: ["review-queue"] }); };
  const ingest = useMutation({ mutationFn: ingestControlledSocialFeed, onSuccess: refresh });
  const activate = useMutation({ mutationFn: activateDemoScenario, onSuccess: refresh });
  if (feed.isLoading || scenarios.isLoading) return <p className="empty-state">Loading controlled demo feed…</p>;
  if (feed.isError || scenarios.isError || !feed.data || !scenarios.data) return <p className="empty-state">The controlled demo feed is unavailable.</p>;
  return <section><header className="page-heading"><p className="eyebrow">Controlled ingestion demo</p><h2>Weather hashtag live feed</h2><p className="status-note">{feed.data.disclaimer}</p><button className="refresh-source" disabled={ingest.isPending} onClick={() => ingest.mutate()}>Ingest matching posts</button>{ingest.data && <p>{ingest.data.created} added · {ingest.data.duplicates} already present</p>}</header><section className="scenario-panel"><h3>Judge-ready scenarios</h3><p>Activate a compact, repeatable incident sequence for the map, review queue, and analytics.</p><div className="scenario-actions">{scenarios.data.map((scenario) => <button key={scenario.id} className="refresh-source" disabled={activate.isPending} onClick={() => activate.mutate(scenario.id)}>{scenario.name} ({scenario.post_count})</button>)}</div>{activate.data && <p>{activate.data.scenario_name ?? "Scenario"}: {activate.data.created} created · {activate.data.duplicates} already present</p>}</section><div className="feed-list">{feed.data.items.map((post) => <article key={post.post_id} className="feed-item"><div><p className="eyebrow">{post.platform} · {post.event_type.replaceAll("_", " ")}</p><h3>{post.city}, {post.state}</h3><p>{post.text}</p><p>{post.hashtags.join(" ")}</p></div><aside><strong>{post.severity}</strong><p>{new Date(post.posted_at).toLocaleString()}</p><p>{post.media.length ? `${post.media.length} media reference${post.media.length > 1 ? "s" : ""}` : "No media reference"}</p></aside></article>)}</div></section>;
}
