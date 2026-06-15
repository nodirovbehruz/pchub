import { BadgePercent } from 'lucide-react';
import CrudPage from '../../components/CrudPage';

const DAYS = '1234567';

const Discounts = () => (
  <CrudPage
    title="Скидки"
    icon={BadgePercent}
    endpoint="/api/v1/loyalty/discounts/"
    columns={[
      { key: 'name', label: 'Название' },
      { key: 'percent', label: 'Скидка', render: r => <span style={{ fontWeight: 600, color: '#10b981' }}>−{r.percent}%</span> },
      { key: 'schedule_days', label: 'Дни', render: r => r.schedule_days || DAYS },
      { key: 'schedule_start', label: 'С', render: r => r.schedule_start?.slice(0,5) || '00:00' },
      { key: 'schedule_end', label: 'По', render: r => r.schedule_end?.slice(0,5) || '00:00' },
      { key: 'telegram_notify', label: 'TG', render: r => r.telegram_notify ? '✅' : '—' },
      { key: 'is_active', label: 'Активна', render: r => r.is_active ? '✅' : '❌' },
    ]}
    formFields={[
      { name: 'name', label: 'Название', type: 'text', required: true, placeholder: 'Открытие клуба' },
      { name: 'percent', label: 'Скидка (%)', type: 'number', required: true, placeholder: '10' },
      { name: 'schedule_days', label: 'Дни недели', type: 'text', defaultValue: DAYS, hint: 'Например 12345 (Пн-Пт) или 1234567 (все)' },
      { name: 'schedule_start', label: 'Время старта (HH:MM)', type: 'time' },
      { name: 'schedule_end', label: 'Время окончания (HH:MM)', type: 'time' },
      { name: 'telegram_notify', label: 'Уведомление в Telegram', type: 'checkbox', hint: 'Слать в TG при использовании' },
      { name: 'is_active', label: 'Активна', type: 'checkbox', defaultValue: true, hint: 'Включена' },
    ]}
  />
);

export default Discounts;
