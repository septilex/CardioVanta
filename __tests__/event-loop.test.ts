/** @jest-environment node */
import { afterStatusUpdate } from "../src/lib/workspace";

test("import status runs synchronously, then as a microtask, then as a timer task", async () => {
  jest.useRealTimers();
  const order: string[] = [];
  const done = afterStatusUpdate(phase => order.push(phase));
  order.push("caller");
  expect(order).toEqual(["sync", "caller"]);
  await done;
  expect(order).toEqual(["sync", "caller", "microtask", "timer"]);
});
