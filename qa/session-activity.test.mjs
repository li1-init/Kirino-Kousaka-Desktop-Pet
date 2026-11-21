import assert from "node:assert/strict";
import {test} from "node:test";
import {createSessionActivity} from "../runtime/session-activity.mjs";

const turn = (method, threadId, id, status) => ({method, params: {threadId, turn: {id, status}}});
const statusOf = (threadId, type) => ({
  method: "thread/status/changed", params: {threadId, status: {type, activeFlags: []}},
});

test("attaching during a task keeps working until the snapshotted turn finishes", () => {
  const changes = [];
  const activity = createSessionActivity((active) => changes.push(active));
  activity.replaceFromSnapshot([{
    id: "thread-a",
    status: {type: "active"},
    turns: [{id: "turn-1", status: "completed"}, {id: "turn-2", status: "inProgress"}],
  }]);
  activity.accept(turn("turn/completed", "thread-a", "turn-1", "completed"));
  assert.equal(activity.active, true);
  activity.accept(turn("turn/completed", "thread-a", "turn-2", "interrupted"));
  assert.deepEqual(changes, [true, false]);
});

test("work remains active through minute boundaries and until its turn ends", (t) => {
  t.mock.timers.enable({apis: ["Date", "setTimeout"]});
  const changes = [];
  const activity = createSessionActivity((active) => changes.push(active));
  activity.accept(turn("turn/started", "thread-a", "turn-1", "inProgress"));
  for (const elapsed of [2460, 57540, 5000, 65000, 120000]) {
    t.mock.timers.tick(elapsed);
    assert.equal(activity.active, true);
  }
  activity.accept(turn("turn/completed", "thread-a", "turn-1", "completed"));
  assert.deepEqual(changes, [true, false]);
});

test("another chat keeps the pet working and duplicate completion is harmless", () => {
  const changes = [];
  const activity = createSessionActivity((active) => changes.push(active));
  activity.accept(turn("turn/started", "thread-a", "turn-1", "inProgress"));
  activity.accept(turn("turn/started", "thread-b", "turn-2", "inProgress"));
  activity.accept(turn("turn/completed", "thread-a", "turn-1", "failed"));
  activity.accept(turn("turn/completed", "thread-a", "turn-1", "failed"));
  assert.equal(activity.active, true);
  activity.accept(turn("turn/started", "thread-b", "turn-3", "inProgress"));
  activity.accept(turn("turn/completed", "thread-b", "turn-2", "interrupted"));
  assert.equal(activity.active, true);
  activity.accept(turn("turn/completed", "thread-b", "turn-3", "interrupted"));
  assert.deepEqual(changes, [true, false]);
});

test("reconnecting reconciles active chats from an authoritative snapshot", () => {
  const changes = [];
  const activity = createSessionActivity((active) => changes.push(active));
  activity.replaceFromSnapshot([{id: "a", status: {type: "active"}}]);
  activity.accept(statusOf("b", "active"));
  activity.accept(statusOf("a", "idle"));
  assert.equal(activity.active, true);
  activity.replaceFromSnapshot([{id: "b", status: {type: "idle"}}]);
  assert.deepEqual(changes, [true, false]);
});
