import type { ProjectDetail } from '../types';
import DepartmentManager from './DepartmentManager';
export default function MemberPermissions({project,expired}:{project:ProjectDetail;expired:()=>void}) {
 const people=[...new Map(project.nodes.filter(n=>n.owner_user_id).map(n=>[n.owner_user_id!,n.owner_display_name??'未命名成員'])).entries()];
 return <section className="panel" aria-label="成員與權限"><h2>專案成員與權限</h2><p>專案負責人：{project.owner_display_name??people.find(([id])=>id===project.owner_user_id)?.[1]??'請由專案管理者確認'}</p><p>可見任務負責人：{people.map(([,name])=>name).join('、')||'尚未指派'}。</p><p>可見任務協作人員／部門：{[...new Set(project.collaborators?.map(c=>c.display_name)??[])].join('、')||'尚未設定'}。可在各節點查看與管理。</p><div className="table-wrap"><table className="data-table"><thead><tr><th>身分</th><th>可操作範圍</th></tr></thead><tbody>{[['系統管理員','同公司專案與部門管理'],['專案負責人','自己的專案：指派、結構、協作、附理由覆寫'],['部門主管','自己的部門：指派任務、核准他人申請；跨部門子樹交專案負責人'],['任務負責人','自己的任務：工作、回報、申請跳過'],['協作人員','可見任務的協作紀錄；不因協作身分取得核准權'],['唯讀人員','檢視，不可寫入']].map(([role,scope])=><tr key={role}><td>{role}</td><td>{scope}</td></tr>)}</tbody></table></div><DepartmentManager expired={expired}/></section>;
}
