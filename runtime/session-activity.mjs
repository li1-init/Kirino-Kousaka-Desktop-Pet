/** Derive pet activity from the host's Codex app-server notifications. */
export function createSessionActivity(onChange) {
  const threads = new Map();
  let active = false;

  function publish() {
    const next = threads.size > 0;
    if (next === active) return;
    active = next;
    onChange(active);
  }

  return {
    get active() {
      return active;
    },

    replaceFromSnapshot(snapshot) {
      const running = snapshot.filter((thread) => thread.status.type === "active");
      const knownTurns = new Map(running.map((thread) => [thread.id, threads.get(thread.id) ?? null]));
      threads.clear();
      for (const [id, turn] of knownTurns) threads.set(id, turn);
      publish();
    },

    accept({method, params}) {
      const id = params?.threadId;
      if (typeof id !== "string") return;

      switch (method) {
        case "turn/started":
          if (params.turn?.status === "inProgress" && typeof params.turn.id === "string") {
            threads.set(id, params.turn.id);
          }
          break;
        case "turn/completed":
          if (["completed", "failed", "interrupted"].includes(params.turn?.status) &&
              threads.get(id) === params.turn.id) {
            threads.delete(id);
          }
          break;
        case "thread/status/changed":
          if (params.status?.type === "active") {
            if (!threads.has(id)) threads.set(id, null);
          } else if (["idle", "systemError", "notLoaded"].includes(params.status?.type)) {
            threads.delete(id);
          }
          break;
      }

      publish();
    },
  };
}
