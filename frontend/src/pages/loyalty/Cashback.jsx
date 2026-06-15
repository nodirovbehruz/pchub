import { Percent } from 'lucide-react';
import CrudPage from '../../components/CrudPage';

const Cashback = () => (
  <CrudPage
    title="Кешбэк"
    icon={Percent}
    endpoint="/api/v1/loyalty/cashback/"
    columns={[
      { key: 'name', label: 'Название' },
      { key: 'deposit_threshold', label: 'Порог пополнения', render: r => `${r.deposit_threshold} сум` },
      { key: 'accrual_type', label: 'Тип', render: r => r.accrual_type === 'percent' ? 'Проценты' : 'Фикс. сумма' },
      { key: 'value', label: 'Значение', render: r => `${r.value}${r.accrual_type === 'percent' ? '%' : 'сум'}` },
      { key: 'valid_until', label: 'До', render: r => r.valid_until ? new Date(r.valid_until).toLocaleDateString('ru-RU') : 'Бессрочно' },
      { key: 'is_active', label: 'Активен', render: r => r.is_active ? '✅' : '❌' },
    ]}
    formFields={[
      { name: 'name', label: 'Название (опционально)', type: 'text', placeholder: '5% от 500сум' },
      { name: 'deposit_threshold', label: 'Сумма пополнения (сум)', type: 'number', required: true, placeholder: '500' },
      { name: 'accrual_type', label: 'Тип начисления', type: 'select', defaultValue: 'percent', options: [
        { value: 'percent', label: 'Проценты (%)' },
        { value: 'fixed', label: 'Фиксированная сумма (сум)' },
      ]},
      { name: 'value', label: 'Значение', type: 'number', required: true, placeholder: '5' },
      { name: 'valid_until', label: 'Действует до (опц.)', type: 'datetime-local' },
      { name: 'is_active', label: 'Активен', type: 'checkbox', defaultValue: true },
    ]}
  />
);

export default Cashback;
