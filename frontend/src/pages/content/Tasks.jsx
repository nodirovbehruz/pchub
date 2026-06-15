import { ClipboardList } from 'lucide-react';
import CrudPage from '../../components/CrudPage';

const Tasks = () => (
  <CrudPage
    title="Задачи"
    icon={ClipboardList}
    endpoint="/api/v1/content/tasks/"
    searchField="title"
    columns={[
      { key: 'title', label: 'Задача' },
      { key: 'is_finished', label: 'Статус', render: r => r.is_finished ? '✅ Завершена' : '⏳ В работе' },
      { key: 'created_at', label: 'Создана', render: r => new Date(r.created_at).toLocaleDateString('ru-RU') },
    ]}
    formFields={[
      { name: 'title', label: 'Название', type: 'text', required: true },
      { name: 'body', label: 'Описание', type: 'textarea' },
      { name: 'is_finished', label: 'Завершена', type: 'checkbox' },
    ]}
  />
);

export default Tasks;
