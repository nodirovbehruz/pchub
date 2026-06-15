import { Gift } from 'lucide-react';
import CrudPage from '../../components/CrudPage';

const Promocodes = () => (
  <CrudPage
    title="Промокоды"
    icon={Gift}
    endpoint="/api/v1/loyalty/promocodes/"
    searchField="code"
    columns={[
      { key: 'code', label: 'Код', render: r => <code style={{ color: '#a78bfa', fontWeight: 600 }}>{r.code}</code> },
      { key: 'name', label: 'Название' },
      { key: 'reward_type', label: 'Тип', render: r => ({
        discount: 'Скидка %', deposit_topup: 'Депозит', bonus_topup: 'Бонусы',
      }[r.reward_type] || r.reward_type) },
      { key: 'value', label: 'Значение', render: r => `${r.value}${r.reward_type === 'discount' ? '%' : 'сум'}` },
      { key: 'usage_count', label: 'Использовано', render: r => `${r.usage_count}/${r.usage_limit || '∞'}` },
      { key: 'is_exhausted', label: 'Статус', render: r =>
        !r.is_active ? '❌ Отключён' : r.is_exhausted ? '⛔ Исчерпан' : '✅ Активен' },
    ]}
    formFields={[
      { name: 'code', label: 'Код', type: 'text', required: true, placeholder: 'WELCOME2026' },
      { name: 'name', label: 'Название', type: 'text', placeholder: 'Приветственный' },
      { name: 'reward_type', label: 'Тип награды', type: 'select', defaultValue: 'discount', options: [
        { value: 'discount', label: 'Скидка (%)' },
        { value: 'deposit_topup', label: 'Пополнить депозит (сум)' },
        { value: 'bonus_topup', label: 'Пополнить бонусы (сум)' },
      ]},
      { name: 'value', label: 'Значение', type: 'number', required: true, placeholder: '20' },
      { name: 'usage_limit', label: 'Лимит использований', type: 'number', defaultValue: 0, hint: '0 = без лимита' },
      { name: 'valid_until', label: 'Действителен до (опционально)', type: 'datetime-local' },
      { name: 'is_active', label: 'Активен', type: 'checkbox', defaultValue: true },
    ]}
  />
);

export default Promocodes;
