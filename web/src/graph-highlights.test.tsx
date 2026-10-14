import {fireEvent, render, screen} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import DependencyGraph from './components/DependencyGraph';
import type {DependencyData} from './types';
const data:DependencyData={nodes:['a','b','c','d','x','y'].map(id=>({id,title:id,status:'doing',blocked:false})),items:[['ab','a','b'],['bc','b','c'],['cd','c','d'],['xy','x','y']].map(([id,predecessor_id,successor_id])=>({id,project_id:'p',predecessor_id,successor_id})),capabilities:{manage:false}};
describe('dependency tracing',()=>{
 it('traces transitive predecessors and successors without highlighting unrelated branches',()=>{
  const {container}=render(<DependencyGraph data={data} select={vi.fn()}/>);
  fireEvent.pointerEnter(screen.getByRole('button',{name:'追蹤相依：b'}),{pointerType:'mouse'});
  expect(container.querySelectorAll('.edge-highlight')).toHaveLength(3);
  expect(container.querySelector('[data-edge-id="xy"]')).toHaveClass('edge-dimmed');
  expect(screen.getByRole('button',{name:'追蹤相依：d'})).toHaveClass('is-related');
  fireEvent.pointerLeave(screen.getByRole('button',{name:'追蹤相依：b'}));
  expect(container.querySelectorAll('.edge-highlight')).toHaveLength(0);
 });
 it('pins across hover changes, opens explicitly, and clears on blank click or Escape',()=>{
  const select=vi.fn();const {container}=render(<DependencyGraph data={data} select={select}/>);
  const b=screen.getByRole('button',{name:'追蹤相依：b'});fireEvent.click(b);
  fireEvent.pointerEnter(screen.getByRole('button',{name:'追蹤相依：x'}),{pointerType:'mouse'});
  expect(b).toHaveAttribute('aria-pressed','true');expect(b).toHaveClass('is-focus');expect(select).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'開啟任務 →'}));expect(select).toHaveBeenCalledWith('b');
  fireEvent.pointerDown(document.body);expect(container.querySelectorAll('.edge-highlight')).toHaveLength(0);
  fireEvent.click(b);fireEvent.keyDown(document,{key:'Escape'});expect(b).toHaveAttribute('aria-pressed','false');
 });
 it('does not present a disappeared pin as a fixed hover in new graph data',()=>{
  const {rerender}=render(<DependencyGraph data={data} select={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'追蹤相依：a'}));
  rerender(<DependencyGraph data={{...data,nodes:data.nodes.filter(n=>n.id!=='a')}} select={vi.fn()}/>);
  fireEvent.pointerEnter(screen.getByRole('button',{name:'追蹤相依：b'}),{pointerType:'mouse'});
  expect(screen.getByRole('status')).toHaveTextContent('預覽：b');expect(screen.queryByRole('button',{name:'開啟任務 →'})).not.toBeInTheDocument();
 });
});
