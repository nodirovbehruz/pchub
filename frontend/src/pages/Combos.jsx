import { Layers } from 'lucide-react';
import CrudPage from '../components/CrudPage';

const Combos = () => (
  <CrudPage
    title="Комбо-наборы"
    icon={Layers}
    endpoint="/api/v1/shops/combos/"
    searchField="name"
    columns={[
      { key: 'name', label: 'Название' },
      { key: 'computer_group_name', label: 'Зал' },
      { key: 'tariff_name', label: 'Тариф', render: r => r.tariff_name || r.tariff || '—' },
      { key: 'sale_price', label: 'Цена', render: r => <span style={{ fontWeight: 600 }}>{r.sale_price} сум</span> },
      { key: 'is_active', label: 'Активен', render: r => r.is_active ? '✅' : '❌' },
    ]}
    formFields={[
      { name: 'name', label: 'Название', type: 'text', required: true, hint: '2–50 символов' },
      { name: 'sale_price', label: 'Цена продажи сум', type: 'number', required: true },
      { name: 'base_price', label: 'Базовая цена сум', type: 'number', defaultValue: 0, hint: 'Сумма позиций до скидки' },
      { name: 'applies_discount', label: 'Применять скидки клуба', type: 'checkbox', defaultValue: true },
      { name: 'is_active', label: 'Активен', type: 'checkbox', defaultValue: true },
    ]}
  />
);

export default Combos;
