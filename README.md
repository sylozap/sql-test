# Тестовое задание: базы данных, SQL, Python

- `sql/tasks/` — SQL-задачи (Часть 2)
- `sql/01_schema.sql`, `sql/02_seed.sql` — схема и тестовые данные
- `tests/test_db_connection.py` — автотест подключения (Часть 3)
- `tests/test_sql_tasks.py` — проверка SQL-задач на тестовых данных

Запуск:

```bash
docker compose up -d --wait
uv sync
uv run pytest -v
DB_PASSWORD=wrong uv run pytest -v tests/test_db_connection.py   # должен упасть
```

Содержание:

- [Часть 1. Теория](#часть-1-теория)
- [Часть 2. SQL-задачи](#часть-2-sql-задачи)
- [Часть 3. Автотест подключения к БД](#часть-3-автотест-подключения-к-бд)

## Часть 1. Теория

### Базовые понятия

#### 1. Что такое СУБД и зачем она нужна, почему не хранить всё в Excel/файлах?

СУБД — это программа, через которую работают с базой данных: она хранит данные, выполняет запросы и следит за тем, чтобы данные не испортились. Приложение отправляет SQL-запрос, а как его выполнить быстрее (какой индекс взять, в каком порядке соединять таблицы), СУБД решает сама.

Excel и файлы перестают справляться, как только с данными одновременно работают несколько человек или данных становится много. Если двое правят один файл, останется версия того, кто сохранил последним. В ячейку можно записать что угодно: дату текстом, отрицательную сумму, номер клиента, которого нет. Транзакций тоже нет: если перевод оборвался на середине, деньги спишутся, но не зачислятся. В СУБД для этого есть блокировки и MVCC, типы и ограничения (`NOT NULL`, `CHECK`, внешние ключи), транзакции и журнал, по которому база восстанавливается после сбоя. Плюс индексы, права доступа и бэкапы. Excel я бы оставил для разовых выгрузок и отчётов.

#### Какие СУБД знаешь, как их можно классифицировать?

Больше всего я работал с PostgreSQL. С ClickHouse сталкивался на учебном задании в институте: на лабораторной по бизнес-аналитике писал OLAP-запросы и делал дашборд в Superset. Из остальных знаю Oracle, MS SQL Server, MySQL, SQLite, из нереляционных MongoDB и Redis.

Делить СУБД можно по разным признакам:

- по модели данных: реляционные (PostgreSQL, Oracle, MS SQL, MySQL) и NoSQL — документные (MongoDB), ключ-значение (Redis), графовые (Neo4j), wide-column (Cassandra);
- по нагрузке: OLTP, где много коротких транзакций (типичное банковское приложение), и OLAP, где тяжёлые аналитические запросы по большим объёмам. ClickHouse как раз OLAP: данные хранятся по столбцам, поэтому агрегаты по большим таблицам считаются быстро, а частые точечные UPDATE ему не подходят;
- по архитектуре: клиент-серверные и встраиваемые (SQLite работает прямо внутри приложения), одноузловые и распределённые.

Kafka, с которой я тоже работал, к СУБД не отношу: это брокер сообщений, хотя данные она хранит на диске, и их можно перечитывать.

#### Что такое реляционная модель?

Это подход, при котором данные лежат в таблицах (в теории они называются отношениями), а связи между таблицами задаются значениями ключей, а не ссылками. У каждой строки есть ключ, по которому её можно однозначно найти. Порядок строк при этом не определён, поэтому без `ORDER BY` на него полагаться нельзя. Модель предложил Кодд в 1970 году, на её математике (реляционной алгебре: выборка, проекция, соединение) построен SQL. Например, в схеме из задания счёт не «содержит» клиента, а хранит его `client_id`.

### Ключи и связи

#### 2. Чем первичный ключ отличается от внешнего?

Первичный ключ идентифицирует строку в своей таблице. Он уникальный, не может быть NULL, и в таблице он один, хотя может состоять из нескольких столбцов. Внешний ключ — это ссылка на первичный (или уникальный) ключ другой таблицы. Его значения могут повторяться (у клиента много счетов), он может быть NULL, если связь необязательная, и СУБД не даст записать в него значение, которого нет в родительской таблице. Можно также задать, что делать при удалении родителя: запретить (`RESTRICT`), удалить связанные строки (`CASCADE`) или обнулить ссылку (`SET NULL`).

Практический момент в PostgreSQL: индекс под первичный ключ создаётся автоматически, а под внешний нет. Его лучше добавить самому, иначе JOIN и удаление родительской строки будут медленными. Поэтому в схеме для задач я добавил индекс на `accounts.client_id`.

#### Какие бывают типы связей? Как реализовать «многие ко многим»?

Один к одному (клиент и паспорт) делается внешним ключом с `UNIQUE`. Один ко многим (клиент и его счета) — внешним ключом на стороне «многих», как `accounts.client_id`. Многие ко многим напрямую не сделать, нужна промежуточная таблица с двумя внешними ключами. Например, если бы у одного счёта могло быть несколько владельцев:

```sql
CREATE TABLE account_owners (
    account_id int  REFERENCES accounts (account_id),
    client_id  int  REFERENCES clients (client_id),
    role       text NOT NULL DEFAULT 'owner',
    PRIMARY KEY (account_id, client_id)
);
```

Составной первичный ключ не даёт дважды привязать одного клиента к одному счёту. В эту же таблицу удобно класть атрибуты самой связи, как `role` здесь.

### Нормализация

#### 3. Что такое нормализация и зачем она нужна?

Нормализация — это разбиение данных по таблицам так, чтобы каждый факт хранился в одном месте. Если записывать ФИО и город клиента прямо в каждую транзакцию, то при переезде клиента придётся обновлять тысячи строк, и где-нибудь обязательно останется старый город. Это аномалия обновления. Кроме неё бывают аномалии вставки (нельзя добавить клиента, у которого ещё нет транзакций) и удаления (удалили последнюю транзакцию и потеряли клиента).

Нормальные формы, если коротко:

- 1НФ — в ячейке одно значение, никаких телефонов через запятую;
- 2НФ — неключевые поля зависят от всего составного ключа, а не от его части;
- 3НФ — неключевые поля не зависят друг от друга: если есть `city_id`, название города должно лежать в справочнике городов, а не рядом.

Для рабочих (OLTP) баз обычно доводят до 3НФ.

#### Когда денормализация оправдана?

Когда чтений намного больше, чем записей, и JOIN-ы становятся узким местом. Типичный случай — аналитика: в хранилищах и витринах специально делают широкие таблицы и схему «звезда». Для ClickHouse это вообще нормальный подход, он лучше работает с одной широкой таблицей, чем с большим количеством JOIN-ов. Есть примеры и в OLTP: хранить текущий баланс счёта, а не пересчитывать его каждый раз по всем транзакциям, или сохранять в заказе адрес и цену на момент покупки (здесь копия данных нужна по смыслу, а не только ради скорости).

Минус в том, что за согласованностью копий приходится следить самому: триггерами, ETL или пересчётом витрин.

### SQL и работа СУБД

#### 4. Чем WHERE отличается от HAVING?

`WHERE` фильтрует строки до группировки, `HAVING` — уже готовые группы после `GROUP BY`. Поэтому агрегаты вроде `COUNT` и `SUM` можно использовать только в `HAVING`. Порядок выполнения такой: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY. Всё, что можно отфильтровать в `WHERE`, лучше фильтровать там: в группировку попадёт меньше строк.

```sql
SELECT client_id, COUNT(*)
FROM accounts
WHERE closed_at IS NULL      -- убираем закрытые счета
GROUP BY client_id
HAVING COUNT(*) > 2;         -- оставляем клиентов, у которых открытых больше двух
```

#### Какие виды JOIN знаешь?

`INNER JOIN` возвращает только строки, для которых нашлась пара. `LEFT JOIN` — все строки левой таблицы, а если пары нет, справа будут NULL. `RIGHT JOIN` — то же самое зеркально, обычно его переписывают в LEFT. `FULL JOIN` возвращает все строки с обеих сторон, `CROSS JOIN` — каждую строку с каждой, без условия. Ещё есть self join, когда таблицу соединяют саму с собой (сотрудник и его руководитель), и `LATERAL` в PostgreSQL, когда подзапрос справа видит текущую строку слева.

Отдельно стоит вспомнить semi- и anti-join, то есть `EXISTS` и `NOT EXISTS`. Синтаксически это не JOIN, но выполняются они как соединения; анти-джойн как раз нужен в задаче 4. И частая ошибка: условие на правую таблицу, вынесенное в `WHERE`, превращает LEFT JOIN в обычный INNER (это встретилось в задаче 3).

#### Чем DELETE, TRUNCATE и DROP отличаются?

`DELETE` удаляет строки, все или по условию `WHERE`. Работает построчно: срабатывают триггеры, проверяются внешние ключи, каждая строка пишется в журнал. На больших таблицах это медленно. Откатывается в рамках транзакции.

`TRUNCATE` очищает таблицу целиком и без условий. Он быстрый, потому что не перебирает строки, а сразу освобождает место. Построчные триггеры не срабатывают, а если на таблицу ссылаются внешние ключи, без `CASCADE` команда не выполнится. В PostgreSQL TRUNCATE можно откатить, а в Oracle и MySQL это DDL с неявным коммитом. Счётчик identity в PostgreSQL сбрасывается, только если указать `RESTART IDENTITY`.

`DROP` удаляет саму таблицу вместе со структурой, индексами и правами.

#### 5. Что такое NULL и как с ним работать?

NULL означает, что значение неизвестно или отсутствует. Это не ноль и не пустая строка. Главное, что надо помнить: любое сравнение с NULL даёт не TRUE и не FALSE, а UNKNOWN, даже `NULL = NULL`. Поэтому `WHERE closed_at = NULL` ничего не вернёт, правильно писать `closed_at IS NULL`.

- `COALESCE(x, 0)` подставляет значение по умолчанию, а `NULLIF(y, 0)` удобен, чтобы не делить на ноль.
- Агрегаты пропускают NULL: `COUNT(*)` считает все строки, `COUNT(col)` — только непустые. `SUM` по пустому набору вернёт NULL, а не 0, поэтому в задаче 3 стоит COALESCE.
- `NOT IN` с подзапросом, где есть хотя бы один NULL, вернёт пустой результат. Поэтому я пишу `NOT EXISTS`.
- В PostgreSQL для сравнения с учётом NULL есть `IS DISTINCT FROM`.

#### Что такое индекс, есть ли у него минусы?

Индекс — это отдельная структура, отсортированная по значениям столбца (чаще всего B-дерево). С ним СУБД сразу находит нужные строки, а не просматривает всю таблицу, как алфавитный указатель в конце книги. В PostgreSQL по умолчанию используется B-tree, он подходит для равенства, диапазонов и сортировки. Для jsonb и массивов есть GIN, для очень больших таблиц, упорядоченных по времени, — BRIN. Индекс бывает составным (тогда важен порядок столбцов), уникальным и частичным, например только по открытым счетам: `WHERE closed_at IS NULL`.

Минусы у индексов есть:

- каждая вставка и обновление должны обновить ещё и все индексы таблицы, поэтому лишние индексы замедляют запись;
- индексы занимают место, со временем разрастаются, и их нужно обслуживать;
- индекс может просто не использоваться: если обернуть столбец в функцию (`EXTRACT(YEAR FROM registered_at) = 2025`), искать по `LIKE '%abc'` или фильтровать только по второму столбцу составного индекса. Поэтому в задаче 1 я написал условие через диапазон дат.

Используется ли индекс на самом деле, видно в `EXPLAIN ANALYZE`.

#### Что такое транзакция?

Транзакция — это набор операций, который выполняется целиком или не выполняется совсем. Классический пример — перевод между счетами: списание и зачисление должны пройти вместе, иначе деньги пропадут или появятся из ниоткуда.

```sql
BEGIN;
UPDATE balances SET amount = amount - 100 WHERE account_id = 101;
UPDATE balances SET amount = amount + 100 WHERE account_id = 104;
COMMIT;   -- если что-то пошло не так, ROLLBACK
```

Свойства транзакций описывают как ACID: атомарность (всё или ничего), согласованность (после транзакции все ограничения выполняются), изолированность (параллельные транзакции не мешают друг другу) и долговечность (после COMMIT данные не пропадут даже при падении сервера).

Изоляция бывает разной строгости. В PostgreSQL по умолчанию Read Committed: транзакция видит только закоммиченные данные, но два одинаковых SELECT внутри одной транзакции могут вернуть разное, если между ними кто-то закоммитил изменения. Строже уровни Repeatable Read и Serializable. Чем строже уровень, тем меньше аномалий, но тем чаще транзакции конфликтуют и их приходится повторять.

## Часть 2. SQL-задачи

Запросы писал под PostgreSQL и проверял на PostgreSQL 18 в Docker. Чтобы было на чём проверять, сделал схему по заданию (добавил CHECK на `tx_type` и `amount` и индексы на внешние ключи) и тестовые данные с неудобными случаями: регистрация 31 декабря и 1 января, закрытые счета, клиенты без счетов, дубли и «почти дубли», транзакция в 23:59:59 последнего дня месяца, одинаковые суммы у двух клиентов. Под каждым запросом его результат на этих данных.

Схема и данные: [sql/01_schema.sql](sql/01_schema.sql), [sql/02_seed.sql](sql/02_seed.sql); решения: [sql/tasks/](sql/tasks/).

### 1. Простая выборка. Клиенты из Новосибирска, зарегистрированные в 2025 году, по дате регистрации

Год проверяю диапазоном, а не через EXTRACT: так условие может использовать индекс по `registered_at`, и не нужно думать о времени внутри последнего дня года.

[sql/tasks/01_simple_select.sql](sql/tasks/01_simple_select.sql)

```sql
-- диапазон, а не EXTRACT(YEAR ...): так может использоваться индекс по registered_at
SELECT client_id, full_name, city, registered_at
FROM clients
WHERE city = 'Новосибирск'
  AND registered_at >= DATE '2025-01-01'
  AND registered_at <  DATE '2026-01-01'
ORDER BY registered_at;
```

| client_id | full_name | city | registered_at |
|---|---|---|---|
| 2 | Петрова Анна Сергеевна | Новосибирск | 2025-01-10 |
| 1 | Иванов Иван Иванович | Новосибирск | 2025-03-15 |
| 7 | Волков Дмитрий Игоревич | Новосибирск | 2025-12-31 |

### 2. Агрегация. Количество открытых счетов в каждой валюте

Открытым считаю счёт без даты закрытия. Писать нужно `IS NULL`, а не `= NULL`.

[sql/tasks/02_open_accounts_by_currency.sql](sql/tasks/02_open_accounts_by_currency.sql)

```sql
SELECT currency, COUNT(*) AS open_accounts
FROM accounts
WHERE closed_at IS NULL
GROUP BY currency
ORDER BY currency;
```

| currency | open_accounts |
|---|---|
| CNY | 1 |
| EUR | 1 |
| RUB | 6 |
| USD | 1 |

### 3. JOIN и агрегация. Имя клиента и общая сумма входящих транзакций

Взял LEFT JOIN, чтобы клиенты без поступлений тоже попали в список с нулём. Условие на `tx_type` поставил в ON: если перенести его в WHERE, такие клиенты отвалятся. Группирую по `client_id`, потому что ФИО может повторяться. Суммы в разных валютах здесь складываются вместе; если это важно, достаточно добавить `a.currency` в GROUP BY.

[sql/tasks/03_incoming_total_by_client.sql](sql/tasks/03_incoming_total_by_client.sql)

```sql
SELECT c.client_id,
       c.full_name,
       COALESCE(SUM(t.amount), 0.00) AS total_in
FROM clients c
LEFT JOIN accounts a     ON a.client_id = c.client_id
LEFT JOIN transactions t ON t.account_id = a.account_id
                        AND t.tx_type = 'in'
GROUP BY c.client_id, c.full_name
ORDER BY total_in DESC, c.client_id;
```

| client_id | full_name | total_in |
|---|---|---|
| 1 | Иванов Иван Иванович | 12000.00 |
| 2 | Петрова Анна Сергеевна | 8001.00 |
| 3 | Сидоров Пётр Андреевич | 3000.00 |
| 4 | Кузнецова Мария Олеговна | 800.00 |
| 5 | Смирнов Алексей Петрович | 0.00 |
| 6 | Попова Елена Викторовна | 0.00 |
| 7 | Волков Дмитрий Игоревич | 0.00 |
| 8 | Морозова Ольга Павловна | 0.00 |

### 4. Анти-джойн. Клиенты без единого счёта

Сделал через NOT EXISTS. Можно и через `LEFT JOIN ... WHERE a.account_id IS NULL`, результат тот же. NOT IN не использую: если в подзапросе попадётся NULL, запрос вернёт пустой результат.

[sql/tasks/04_clients_without_accounts.sql](sql/tasks/04_clients_without_accounts.sql)

```sql
SELECT c.client_id, c.full_name
FROM clients c
WHERE NOT EXISTS (
    SELECT 1 FROM accounts a WHERE a.client_id = c.client_id
)
ORDER BY c.client_id;
```

| client_id | full_name |
|---|---|
| 6 | Попова Елена Викторовна |
| 8 | Морозова Ольга Павловна |

### 5. HAVING. Клиенты, у которых больше двух счетов

Считаю все счета, включая закрытые, потому что в условии не сказано иначе. Если нужны только открытые, достаточно добавить `WHERE a.closed_at IS NULL`.

[sql/tasks/05_clients_with_more_than_two_accounts.sql](sql/tasks/05_clients_with_more_than_two_accounts.sql)

```sql
SELECT c.client_id, c.full_name, COUNT(*) AS accounts_cnt
FROM clients c
JOIN accounts a ON a.client_id = c.client_id
GROUP BY c.client_id, c.full_name
HAVING COUNT(*) > 2
ORDER BY accounts_cnt DESC;
```

| client_id | full_name | accounts_cnt |
|---|---|---|
| 3 | Сидоров Пётр Андреевич | 4 |
| 1 | Иванов Иван Иванович | 3 |

### 6. Дубли. Задвоенные транзакции (одинаковые account_id, tx_date, amount)

Группирую по трём полям и оставляю группы, где больше одной строки. Через ARRAY_AGG собираю id, чтобы сразу было видно, какие именно транзакции задвоены. Закомментированный запрос нумерует копии внутри группы; строки с `rn > 1` лишние, если дубли нужно удалить.

[sql/tasks/06_duplicate_transactions.sql](sql/tasks/06_duplicate_transactions.sql)

```sql
SELECT account_id, tx_date, amount,
       COUNT(*) AS cnt,
       ARRAY_AGG(tx_id ORDER BY tx_id) AS tx_ids
FROM transactions
GROUP BY account_id, tx_date, amount
HAVING COUNT(*) > 1
ORDER BY account_id, tx_date;

-- лишние копии (если нужно удалить дубли, оставив по одной):
-- SELECT *
-- FROM (SELECT t.*,
--              ROW_NUMBER() OVER (PARTITION BY account_id, tx_date, amount ORDER BY tx_id) AS rn
--       FROM transactions t) d
-- WHERE rn > 1;
```

| account_id | tx_date | amount | cnt | tx_ids |
|---|---|---|---|---|
| 101 | 2025-05-10 08:15:00 | 500.00 | 3 | {8,9,10} |
| 104 | 2025-05-01 12:00:00 | 1500.50 | 2 | {3,4} |

### 7. Оконные функции. Топ-3 клиентов по сумме исходящих транзакций в каждом месяце

Сначала считаю сумму исходящих по каждому клиенту за месяц, потом нумерую клиентов внутри месяца по убыванию суммы и беру первых трёх. Выбрал ROW_NUMBER, чтобы в каждом месяце было ровно три строки. В июле у двух клиентов одинаково по 300, и с DENSE_RANK получилось бы четыре строки. Как считать равные суммы, я бы уточнил у того, кто ставит задачу.

[sql/tasks/07_top3_outgoing_by_month.sql](sql/tasks/07_top3_outgoing_by_month.sql)

```sql
WITH monthly_out AS (
    SELECT date_trunc('month', t.tx_date)::date AS month,
           a.client_id,
           SUM(t.amount) AS total_out
    FROM transactions t
    JOIN accounts a ON a.account_id = t.account_id
    WHERE t.tx_type = 'out'
    GROUP BY 1, 2
),
ranked AS (
    SELECT m.*,
           ROW_NUMBER() OVER (PARTITION BY month ORDER BY total_out DESC, client_id) AS rn
    FROM monthly_out m
)
SELECT r.month, r.rn, r.client_id, c.full_name, r.total_out
FROM ranked r
JOIN clients c ON c.client_id = r.client_id
WHERE r.rn <= 3
ORDER BY r.month, r.rn;
```

| month | rn | client_id | full_name | total_out |
|---|---|---|---|---|
| 2025-05-01 | 1 | 1 | Иванов Иван Иванович | 2500.00 |
| 2025-05-01 | 2 | 2 | Петрова Анна Сергеевна | 1000.00 |
| 2025-05-01 | 3 | 4 | Кузнецова Мария Олеговна | 700.00 |
| 2025-06-01 | 1 | 3 | Сидоров Пётр Андреевич | 900.00 |
| 2025-06-01 | 2 | 4 | Кузнецова Мария Олеговна | 400.00 |
| 2025-06-01 | 3 | 1 | Иванов Иван Иванович | 100.00 |
| 2025-07-01 | 1 | 2 | Петрова Анна Сергеевна | 300.00 |
| 2025-07-01 | 2 | 4 | Кузнецова Мария Олеговна | 300.00 |
| 2025-07-01 | 3 | 1 | Иванов Иван Иванович | 50.00 |

## Часть 3. Автотест подключения к БД

Взял PostgreSQL: он у меня уже есть в Docker, и SQL-задачи тоже под него. Драйвер — psycopg 3, тесты на pytest, окружение и зависимости через uv. Параметры подключения тест берёт из переменных окружения, а значения по умолчанию совпадают с [docker-compose.yml](docker-compose.yml). Так пароль не зашит в код, а для проверки падения достаточно подменить одну переменную.

```bash
docker compose up -d --wait        # поднять PostgreSQL
uv sync                            # pytest + psycopg[binary]
uv run pytest -v tests/test_db_connection.py
DB_PASSWORD=wrong uv run pytest -v tests/test_db_connection.py
```

Неверный пароль можно задать в Environment variables конфигурации запуска.

### [tests/conftest.py](tests/conftest.py)

```python
import os

import pytest


@pytest.fixture(scope="session")
def db_params():
    # по умолчанию - то, что в docker-compose.yml
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "bank"),
        "user": os.getenv("DB_USER", "intern"),
        "password": os.getenv("DB_PASSWORD", "intern_pass"),
        "connect_timeout": 5,
    }
```

### [tests/test_db_connection.py](tests/test_db_connection.py)

Первый тест подключается, выполняет `select now()` и проверяет, что вернулась дата и что она близка к текущему времени. Второй проверяет обратное: с неправильным паролем подключение должно падать с OperationalError.

```python
from datetime import datetime, timedelta, timezone

import psycopg
import pytest


def test_connection_and_select_now(db_params):
    with psycopg.connect(**db_params) as conn:
        row = conn.execute("select now()").fetchone()

    assert row is not None
    db_now = row[0]
    assert isinstance(db_now, datetime)
    # время сервера должно быть примерно текущим
    assert abs(datetime.now(timezone.utc) - db_now) < timedelta(minutes=1)


def test_wrong_password_is_rejected(db_params):
    params = dict(db_params, password="definitely_wrong")
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(**params)
```

### Успешный прогон

```
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.7.0 -- /home/user/projects/sql/.venv/bin/python
rootdir: /home/user/projects/sql
configfile: pyproject.toml
collecting ... collected 2 items

tests/test_db_connection.py::test_connection_and_select_now PASSED       [ 50%]
tests/test_db_connection.py::test_wrong_password_is_rejected PASSED      [100%]

============================== 2 passed in 0.12s ===============================
```

### Прогон с неверным паролем

Основной тест падает с `password authentication failed for user "intern"`. Второй тест при этом проходит, так и должно быть.

```
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.7.0 -- /home/user/projects/sql/.venv/bin/python
rootdir: /home/user/projects/sql
configfile: pyproject.toml
collecting ... collected 2 items

tests/test_db_connection.py::test_connection_and_select_now FAILED       [ 50%]
tests/test_db_connection.py::test_wrong_password_is_rejected PASSED      [100%]

=================================== FAILURES ===================================
________________________ test_connection_and_select_now ________________________
tests/test_db_connection.py:8: in test_connection_and_select_now
    with psycopg.connect(**db_params) as conn:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.12/site-packages/psycopg/connection.py:126: in connect
    raise last_ex.with_traceback(None)
E   psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "intern"
=========================== short test summary info ============================
FAILED tests/test_db_connection.py::test_connection_and_select_now - psycopg....
========================= 1 failed, 1 passed in 0.15s ==========================
```

### Дополнительно

Решения SQL-задач тоже обложил тестами ([tests/test_sql_tasks.py](tests/test_sql_tasks.py)): каждый тест создаёт схему с данными в транзакции, выполняет запрос из `sql/tasks`, сверяет результат и откатывается.

```
============================= test session starts ==============================
platform linux -- Python 3.12.14, pytest-9.1.1, pluggy-1.7.0 -- /home/user/projects/sql/.venv/bin/python
rootdir: /home/user/projects/sql
configfile: pyproject.toml
testpaths: tests
collecting ... collected 9 items

tests/test_db_connection.py::test_connection_and_select_now PASSED       [ 11%]
tests/test_db_connection.py::test_wrong_password_is_rejected PASSED      [ 22%]
tests/test_sql_tasks.py::test_task1 PASSED                               [ 33%]
tests/test_sql_tasks.py::test_task2 PASSED                               [ 44%]
tests/test_sql_tasks.py::test_task3 PASSED                               [ 55%]
tests/test_sql_tasks.py::test_task4 PASSED                               [ 66%]
tests/test_sql_tasks.py::test_task5 PASSED                               [ 77%]
tests/test_sql_tasks.py::test_task6 PASSED                               [ 88%]
tests/test_sql_tasks.py::test_task7 PASSED                               [100%]

============================== 9 passed in 0.46s ===============================
```
