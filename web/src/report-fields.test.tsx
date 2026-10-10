import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import ReportFieldEditor, { FieldDefinitions, ReportFieldInputs } from './components/ReportFieldEditor';
import ReportPanel, { ReportSummary } from './components/ReportPanel';
import { api, ApiError } from './api';
import type { ReportField, Report } from './types';

const field: ReportField = {id:'f',label:'重量',type:'number',unit:'kg',required:true,options:[]};

describe('custom report fields', () => {
  it('adds, orders and removes definitions without modifying existing identity', () => {
    function Editor() { const [fields, setFields] = useState<ReportField[]>([field]); return <FieldDefinitions fields={fields} changed={setFields} />; }
    render(<Editor />);
    fireEvent.change(screen.getByLabelText('欄位名稱'), {target:{value:'驗證結果'}});
    fireEvent.change(screen.getByLabelText('欄位類型'), {target:{value:'select'}});
    fireEvent.change(screen.getByLabelText('選項（以逗號分隔）'), {target:{value:'合格、不合格'}});
    fireEvent.click(screen.getByRole('button',{name:'新增欄位'}));
    fireEvent.click(screen.getByRole('button',{name:'上移 驗證結果'}));
    expect(screen.getAllByRole('listitem')[0]).toHaveTextContent('驗證結果');
    fireEvent.click(screen.getByRole('button',{name:'移除 重量'}));
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
  });
  it('retains definitions after a version conflict and does not repeat a write', async () => {
    vi.spyOn(api,'reportFields').mockResolvedValue({fields:[field],version:1,active:true,can_edit:true});
    const save = vi.spyOn(api,'saveReportFields').mockRejectedValue(new ApiError(409,'回報欄位已變更，請重新載入'));
    render(<ReportFieldEditor nodeId="n" expired={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button',{name:'移除 重量'}));
    fireEvent.click(screen.getByRole('button',{name:'儲存回報欄位'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('輸入已保留');
    expect(screen.queryByText('重量 · 數字（kg） · 必填')).not.toBeInTheDocument();
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith('n',1,[],expect.any(AbortSignal));
  });
  it('disables editing when the API denies it', async () => {
    vi.spyOn(api,'reportFields').mockResolvedValue({fields:[field],version:1,active:true,can_edit:false});
    render(<ReportFieldEditor nodeId="n" expired={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole('button',{name:'新增欄位'})).toBeDisabled());
    expect(screen.queryByRole('button',{name:'儲存回報欄位'})).not.toBeInTheDocument();
  });
  it('renders zero and escaped historical text, and preserves number input zero', () => {
    const changed=vi.fn();
    render(<ReportFieldInputs fields={[field]} values={{f:'0'}} changed={changed} />);
    expect(screen.getByRole('spinbutton')).toHaveValue(0);
    render(<ReportSummary report={{fields:[{...field,value:0,order:0},{...field,id:'s',unit:'',label:'<script>標籤</script>',value:'<img onerror=x>',order:1}],summary:'完成',version:1,status:'approved'} as Report} />);
    expect(screen.getByText('0 kg')).toBeVisible();
    expect(screen.getByText('<img onerror=x>')).toBeVisible();
    expect(document.querySelector('script')).toBeNull();
  });
  it('waits for rejected history before prefilling an automatically opened form', async () => {
    let resolveHistory!: (value: unknown) => void;
    vi.spyOn(api,'records').mockImplementation(() => new Promise(resolve => { resolveHistory = resolve as (value: unknown) => void; }));
    const fields = vi.spyOn(api,'reportFields').mockResolvedValue({fields:[field],version:1,active:true,can_edit:true});
    vi.spyOn(api,'quota').mockResolvedValue({charged_bytes:0,limit_bytes:1000,remaining_bytes:1000});
    const node = {id:'n',status:'doing',capabilities:{submit_report:true},state_actions:['submit_report']} as import('./types').NodeItem;
    render(<ReportPanel node={node} userId="u" reload={async()=>{}} expired={vi.fn()} autoOpen />);
    expect(fields).not.toHaveBeenCalled();
    resolveHistory({items:[{type:'report',id:'r',version:1,status:'rejected',summary:'舊回報',result:'達成',finished_on:'2026-10-10',fields:[{...field,order:0,value:0}]}],next_cursor:null});
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(0));
    fireEvent.change(screen.getByRole('spinbutton'),{target:{value:'-2'}});
    fireEvent.click(screen.getByRole('button',{name:'重新載入回報欄位（保留相同欄位輸入）'}));
    await waitFor(() => expect(fields).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('spinbutton')).toHaveValue(-2);
  });
});
