import { Trophy } from 'lucide-react';
import CrudPage from '../../components/CrudPage';

const TRIGGER_LABELS = {
  registration: 'За регистрацию',
  topup_single: 'Разовое пополнение ≥',
  topup_total: 'Всего пополнено ≥',
  spend_single: 'Разовая трата ≥',
  spend_total: 'Всего потрачено ≥',
  hours_in_club: 'Часов в клубе ≥',
};

const REWARD_LABELS = {
  none: 'Без награды',
  discount: 'Скидка %',
  bonus: 'Бонусы (сум)',
};

const Achievements = () => (
  <CrudPage
    title="Достижения"
    icon={Trophy}
    endpoint="/api/v1/loyalty/achievements/"
    columns={[
      { key: 'name', label: 'Название' },
      { key: 'trigger_type', label: 'Условие', render: r => TRIGGER_LABELS[r.trigger_type] || r.trigger_type },
      { key: 'threshold', label: 'Порог', render: r => r.threshold || '—' },
      { key: 'reward_type', label: 'Награда', render: r => REWARD_LABELS[r.reward_type] || r.reward_type },
      { key: 'reward_value', label: 'Размер', render: r =>
        r.reward_type === 'none' ? '—' :
        r.reward_type === 'discount' ? `${r.reward_value}%` : `${r.reward_value}сум` },
      { key: 'is_active', label: 'Активно', render: r => r.is_active ? '✅' : '❌' },
    ]}
    formFields={[
      { name: 'name', label: 'Название', type: 'text', required: true, placeholder: 'Новичок' },
      { name: 'description', label: 'Описание', type: 'textarea', placeholder: 'За регистрацию в клубе' },
      { name: 'trigger_type', label: 'Условие', type: 'select', defaultValue: 'registration', options: [
        { value: 'registration', label: 'За регистрацию' },
        { value: 'topup_single', label: 'Разовое пополнение ≥' },
        { value: 'topup_total', label: 'Всего пополнено ≥' },
        { value: 'spend_single', label: 'Разовая трата ≥' },
        { value: 'spend_total', label: 'Всего потрачено ≥' },
        { value: 'hours_in_club', label: 'Часов в клубе ≥' },
      ]},
      { name: 'threshold', label: 'Порог (если применимо)', type: 'number', defaultValue: 0 },
      { name: 'reward_type', label: 'Тип награды', type: 'select', defaultValue: 'none', options: [
        { value: 'none', label: 'Без награды' },
        { value: 'discount', label: 'Скидка (%)' },
        { value: 'bonus', label: 'Бонусы (сум)' },
      ]},
      { name: 'reward_value', label: 'Размер награды', type: 'number', defaultValue: 0 },
      { name: 'is_active', label: 'Активно', type: 'checkbox', defaultValue: true },
    ]}
  />
);

export default Achievements;
