import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Dropdown from './components/Dropdown';

describe('header and action disclosures', () => {
  it('shows the first option as the trigger label and restores focus before opening an action', () => {
    let origin: Element | null = null;
    const save = vi.fn(() => { origin = document.activeElement; });
    render(<Dropdown name="專案操作" label="另存為模板" closeOnAction><button onClick={save}>另存為模板</button><button disabled>套用模板</button><button>新增子節點</button></Dropdown>);
    const trigger=screen.getByRole('button',{name:'專案操作'});
    expect(trigger).toHaveTextContent('另存為模板');
    expect(screen.queryByRole('button',{name:'新增子節點'})).not.toBeInTheDocument();
    fireEvent.click(trigger);
    expect(screen.getByRole('button',{name:'套用模板'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'另存為模板'}));
    expect(save).toHaveBeenCalledOnce();
    expect(origin).toBe(trigger);
    expect(trigger).toHaveAttribute('aria-expanded','false');
    expect(trigger).toHaveFocus();
  });
  it('keeps account controls open on internal interaction and returns focus with Escape', () => {
    render(<Dropdown name="使用者選單" label="游專案"><button>取消切換</button></Dropdown>);
    const trigger=screen.getByRole('button',{name:'使用者選單'});
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole('button',{name:'取消切換'}));
    expect(trigger).toHaveAttribute('aria-expanded','true');
    fireEvent.keyDown(document,{key:'Escape'});
    expect(trigger).toHaveAttribute('aria-expanded','false');
    expect(trigger).toHaveFocus();
  });
});
