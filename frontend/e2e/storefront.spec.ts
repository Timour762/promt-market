import { test,expect } from '@playwright/test';
test('catalog search, filters and real product page',async({page})=>{
 await page.goto('/catalog');await expect(page.getByRole('heading',{name:'Меньше попыток.'})).toBeVisible();
 const cards=page.locator('.pv-card');await expect(cards).toHaveCount(6);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
 await page.getByRole('textbox',{name:'Найти промпт'}).fill('Python');await expect(cards).toHaveCount(1);
 await page.getByRole('link',{name:'Senior Python Developer',exact:true}).click();await expect(page.getByRole('heading',{name:'Senior Python Developer',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'От задачи к структуре ответа'})).toBeVisible();
 await page.reload();await expect(page.getByRole('heading',{name:'Senior Python Developer',exact:true})).toBeVisible();
 await page.goto('/catalog');await page.getByRole('textbox',{name:'Найти промпт'}).fill('unfindable_fixture');await expect(page.getByRole('heading',{name:'Пока ничего не нашлось'})).toBeVisible();
 await page.getByRole('button',{name:'Сбросить фильтры'}).click();await expect(cards).toHaveCount(6);
 await page.getByRole('button',{name:/Бизнес/}).click();await expect(cards).toHaveCount(1);
 await expect.poll(()=>page.locator('.pv-card img').evaluateAll(images=>images.every(img=>(img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth>0))).toBe(true);
});
test('navigation, keyboard, auth forms and legal pages fit viewport',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 for(const path of ['/','/catalog','/login','/register','/forgot-password','/legal/privacy','/legal/contacts']){
   await page.goto(path);await expect(page.locator('h1')).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),path).toBe(true);
 }
 await expect(page.getByText('promtmarket@mail.ru — вопросы',{exact:false})).toBeVisible();
 await page.goto('/login');await page.getByLabel('Логин или email').focus();await page.keyboard.press('Tab');await expect(page.getByLabel('Пароль',{exact:true})).toBeFocused();
 await expect(page.getByLabel('Логин или email')).toBeVisible();await expect(page.getByLabel('Пароль',{exact:true})).toHaveAttribute('type','password');
 await page.goto('/account/library');await expect(page).toHaveURL(/\/login/);
 expect(errors).toEqual([]);
});
