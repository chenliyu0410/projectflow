import { fireEvent, render } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import useScrollActivity from './useScrollActivity';

function Probe() { useScrollActivity(); return <div data-testid="box" style={{ overflowY: 'auto' }}><span data-testid="inner">內容</span></div>; }
afterEach(() => vi.restoreAllMocks());

it('measures layout at most once per animation frame while the pointer moves', () => {
  const frames: FrameRequestCallback[] = [];
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { frames.push(callback); return frames.length; });
  vi.stubGlobal('cancelAnimationFrame', vi.fn());
  const view = render(<Probe />);
  const box = view.getByTestId('box');
  Object.defineProperty(box, 'scrollHeight', { value: 200 });
  Object.defineProperty(box, 'clientHeight', { value: 100 });
  box.getBoundingClientRect = () => ({ left: 0, top: 0, right: 100, bottom: 100, width: 100, height: 100, x: 0, y: 0, toJSON: () => ({}) });
  const styles = vi.spyOn(window, 'getComputedStyle');
  for (let x = 90; x < 100; x++) fireEvent.pointerMove(view.getByTestId('inner'), { clientX: x, clientY: 10, pointerType: 'mouse' });
  // 移動時不立刻量版面，等下一幀只量最後一次的位置。
  expect(styles).not.toHaveBeenCalled();
  expect(frames).toHaveLength(1);
  frames.shift()!(0);
  expect(box.dataset.scrollActive).toBe('true');
  expect(styles.mock.calls.length).toBeLessThanOrEqual(2);
});
