import { Wrench } from 'lucide-react';
import CrudPage from '../components/CrudPage';

const StoreServices = () => (
  <CrudPage
    title="Услуги"
    icon={Wrench}
    endpoint="/api/v1/shops/services/"
    searchField="name"
    columns={[
      { key: 'name',        label: 'Название',  style: { fontWeight: 500 } },
      { key: 'description', label: 'Описание',  render: r => r.description || '—' },
      { key: 'price',       label: 'Цена',      render: r => `${r.price} сум` },
      { key: 'is_active',   label: 'Активна',   render: r => r.is_active ? '✅' : '❌' },
    ]}
    formFields={[
      { name: 'name',        label: 'Название *',     type: 'text',     required: true },
      { name: 'description', label: 'Описание',       type: 'textarea' },
      { name: 'price',       label: 'Цена (сум) *',    type: 'number',   required: true },
      { name: 'is_active',   label: 'Активна',       type: 'checkbox' },
    ]}
  />
);

export default StoreServices;
