import point
import actions

BLOB_RATE_SCALE = 4

QUAKE_STEPS = 10
QUAKE_DURATION = 1100

 
class WorldObject(object):
#Contains all objects; Background and Obstacle exclusively in this class
   def __init__(self, name, imgs):
      self.name = name
      self.imgs = imgs
      self.current_img = 0

   def get_name(self):
      return self.name

   def get_images(self):
      return self.imgs

   def get_image(self):
      return self.imgs[self.current_img]
	  
   def next_image(self):
      self.current_img = (self.current_img + 1) % len(self.imgs)


class Background(WorldObject):
   pass


class Obstacle(WorldObject):
   def __init__(self, name, position, imgs):
      super(Obstacle, self).__init__(name, imgs)
      self.position = position

   def set_position(self, point):
      self.position = point

   def get_position(self):
      return self.position
      
   def schedule_entity(self, world, i_store):
      pass	 

   
class Entity(WorldObject):
#Contains StaticEntity(Vein, Ore, Quake), Individual(MovingEntity, Blacksmith)
   def __init__(self, name, imgs, position):
      super(Entity, self).__init__(name, imgs)
      self.position = position

   def set_position(self, point):
      self.position = point

   def get_position(self):
      return self.position
      
   def schedule_entity(self, world, i_store):
      pass

   def schedule_action(self, world, action, time):
      self.add_pending_action(action)
      world.schedule_action(action, time)

   def schedule_animation(self, world, repeat_count=0):
      self.schedule_action(world, 
         self.create_animation_action(world, repeat_count),
         self.get_animation_rate())
         
         
   def create_animation_action(self, world, repeat_count):
      def action(current_ticks):
         self.remove_pending_action(action)

         self.next_image()

         if repeat_count != 1:
            self.schedule_action(world, 
               self.create_animation_action(world, max(repeat_count - 1, 0)),
               current_ticks + self.get_animation_rate())

         return [self.get_position()]
      return action
      
      
   def remove_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.remove(action)

   def add_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.append(action)

   def get_pending_actions(self):
      if hasattr(self, "pending_actions"):
         return self.pending_actions
      else:
         return []

   def clear_pending_actions(self):
      if hasattr(self, "pending_actions"):
         self.pending_actions = []
      
   def remove_entity(self, world):
      for action in self.get_pending_actions():
         world.unschedule_action(action)
      self.clear_pending_actions()
      world.remove_entity(self)

      
class Individual(Entity):
#Contains MovingEntity (Miner, OreBlob), Blacksmith
   def __init__(self, name, imgs, position, rate):
      super(Individual, self).__init__(name, imgs, position)
      self.rate = rate
      self.pending_actions = []
      
   def get_rate(self):
      return self.rate


class MovingEntity(Individual):
#Contains Miner, OreBlob
   def __init__(self, name, imgs, position, rate, animation_rate):
      super(MovingEntity, self).__init__(name, imgs, position, rate)
      self.animation_rate = animation_rate
      
   def get_animation_rate(self):
      return self.animation_rate

   def schedule_self(self, world, ticks, i_store):
      self.schedule_action(world, self.create_self_action(world, i_store),
         ticks + self.get_rate())
      self.schedule_animation(world)

      
   def next_position(self, world, dest_pt):
      horiz = actions.sign(dest_pt.x - self.position.x)
      new_pt = point.Point(self.position.x + horiz, self.position.y)

      if horiz == 0 or world.is_occupied(new_pt):
         vert = actions.sign(dest_pt.y - self.position.y)
         new_pt = point.Point(self.position.x, self.position.y + vert)

         if vert == 0 or world.is_occupied(new_pt):
            new_pt = point.Point(self.position.x, self.position.y)

      return new_pt


   def find_nearest_entity(self, pt):
      return pt.distance_sq(self.get_position())

      
class Miner(MovingEntity):
   def __init__(self, name, resource_limit, position, rate, imgs, 
      animation_rate):
      super(Miner, self).__init__(name, imgs, position, rate, animation_rate)
      self.resource_limit = resource_limit

   def get_resource_limit(self):
      return self.resource_limit
	  
   def set_resource_count(self, n):
      self.resource_count = n

   def get_resource_count(self):
      return self.resource_count


   def create_self_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         entity_pt = self.get_position()
         to_entity = world.find_nearest(entity_pt, self.to_entity())
         (tiles, found) = self.miner_to_entity(world, to_entity)

         new_entity = self
         if found:
            new_entity = self.try_transform_miner(world, 
               self.try_transform_miner_status)

         new_entity.schedule_action(world, 
            new_entity.create_self_action(world, i_store),
            current_ticks + new_entity.get_rate())
         return tiles
      return action
      
      
   def miner_to_entity(self, world, entity):
      entity_pt = self.get_position()
      if not entity:
         return ([entity_pt], False)
      to_pt = entity.get_position()
      if entity_pt.adjacent(to_pt):
         return self.miner_to(world, entity)
      else:
         new_pt = self.next_position(world, to_pt)
         return (world.move_entity(self, new_pt), False)
      
 
   def try_transform_miner(self, world, transform):
      new_entity = transform(world)
      if self != new_entity:
         world.clear_pending_actions(self)
         world.remove_entity_at(self.get_position())
         world.add_entity(new_entity)
         new_entity.schedule_animation(world)

      return new_entity


class MinerNotFull(Miner):
   def __init__(self, name, resource_limit, position, rate, imgs,
      animation_rate):
      super(MinerNotFull, self).__init__(name, resource_limit, position, 
         rate, imgs, animation_rate)
      self.resource_count = 0
      
   def schedule_entity(self, world, i_store):
      self.schedule_self(world, 0, i_store)
      
   def to_entity(self):
      return Ore

   def miner_to(self, world, ore):
      ore_pt = ore.get_position()
      self.set_resource_count(1 + self.get_resource_count())
      ore.remove_entity(world)
      return ([ore_pt], True)
       
   def try_transform_miner_status(self, world):
      if self.resource_count < self.resource_limit:
         return self
      else:
         new_entity = MinerFull(
            self.get_name(), self.get_resource_limit(),
            self.get_position(), self.get_rate(),
            self.get_images(), self.get_animation_rate())
         return new_entity


class MinerFull(Miner):
   def __init__(self, name, resource_limit, position, rate, imgs,
      animation_rate):
      super(MinerFull, self).__init__(name, resource_limit, position, 
	     rate, imgs, animation_rate)
      self.resource_count = resource_limit
      
   def to_entity(self):
      return Blacksmith
      
   def miner_to(self, world, smith):
      smith.set_resource_count(smith.get_resource_count() 
         + self.get_resource_count())
      self.set_resource_count(0)
      return ([], True)
		 
   def try_transform_miner_status(self, world):
      new_entity = MinerNotFull(
         self.get_name(), self.get_resource_limit(),
         self.get_position(), self.get_rate(),
         self.get_images(), self.get_animation_rate())
      return new_entity


class OreBlob(MovingEntity):
   def __init__(self, name, position, rate, imgs, animation_rate):
      super(OreBlob, self).__init__(name, imgs, position, rate, animation_rate)


   def next_position(self, world, dest_pt):
      horiz = actions.sign(dest_pt.x - self.position.x)
      new_pt = point.Point(self.position.x + horiz, self.position.y)

      if horiz == 0 or (world.is_occupied(new_pt) and
         not isinstance(world.get_tile_occupant(new_pt), Ore)):
         vert = actions.sign(dest_pt.y - self.position.y)
         new_pt = point.Point(self.position.x, self.position.y + vert)

         if vert == 0 or (world.is_occupied(new_pt) and
            not isinstance(world.get_tile_occupant(new_pt), Ore)):
            new_pt = point.Point(self.position.x, self.position.y)

      return new_pt
 

   def create_self_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         entity_pt = self.get_position()
         vein = world.find_nearest(entity_pt, Vein)
         (tiles, found) = self.blob_to_vein(world, vein)

         next_time = current_ticks + self.get_rate()
         if found:
            quake = actions.create_quake(world, tiles[0], current_ticks, 
               i_store)
            world.add_entity(quake)
            next_time = current_ticks + self.get_rate() * 2

         self.schedule_action(world, 
            self.create_self_action(world, i_store), next_time)

         return tiles
      return action
      

   def blob_to_vein(self, world, vein):
      entity_pt = self.get_position()
      if not vein:
         return ([entity_pt], False)
      vein_pt = vein.get_position()
      if entity_pt.adjacent(vein_pt):
         vein.remove_entity(world)
         return ([vein_pt], True)
      else:
         new_pt = self.next_position(world, vein_pt)
         old_entity = world.get_tile_occupant(new_pt)
         if isinstance(old_entity, Ore):
            old_entity.remove_entity(world)
         return (world.move_entity(self, new_pt), False)


class Blacksmith(Individual):
   def __init__(self, name, position, imgs, resource_limit, rate,
      resource_distance=1):
      super(Blacksmith, self).__init__(name, imgs, position, rate)
      self.resource_limit = resource_limit
      self.resource_count = 0
      self.resource_distance = resource_distance
    
   def get_resource_limit(self):
      return self.resource_limit
	  
   def set_resource_count(self, n):
      self.resource_count = n

   def get_resource_count(self):
      return self.resource_count

   def get_resource_distance(self):
      return self.resource_distance


class StaticEntity(Entity):
#Contains Vein, Ore, Quake
   def __init__(self, name, imgs, position):
      super(StaticEntity, self).__init__(name, imgs, position)
      self.pending_actions = []

   def schedule_self(self, world, ticks, i_store):
      self.schedule_action(world, self.create_self_action(world, 
         i_store), ticks + self.get_rate())

    
class Vein(StaticEntity):
   def __init__(self, name, rate, position, imgs, resource_distance=1):
      super(Vein, self).__init__(name, imgs, position)
      self.rate = rate
      self.resource_distance = resource_distance
      
   def get_rate(self):
      return self.rate

   def get_resource_distance(self):
      return self.resource_distance
      
   def schedule_entity(self, world, i_store):
      self.schedule_self(world, 0, i_store)

      
   def create_self_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)

         open_pt = self.find_open_around(world)
         if open_pt:
            ore = actions.create_ore(world,
               "ore - " + self.get_name() + " - " + str(current_ticks),
               open_pt, current_ticks, i_store)
            world.add_entity(ore)
            tiles = [open_pt]
         else:
            tiles = []

         self.schedule_action(world, 
            self.create_self_action(world, i_store),
            current_ticks + self.get_rate())
         return tiles
      return action
	  

   def find_open_around(self, world):
      for dy in range(-self.get_resource_distance(), 
	     self.get_resource_distance() + 1):
         for dx in range(-self.get_resource_distance(), 
		    self.get_resource_distance() + 1):
            new_pt = point.Point(self.position.x + dx, self.position.y + dy)

            if (world.within_bounds(new_pt) and
               (not world.is_occupied(new_pt))):
               return new_pt

      return None
		   

class Ore(StaticEntity):
   def __init__(self, name, position, imgs, rate=5000):
      super(Ore, self).__init__(name, imgs, position)
      self.rate = rate

   def get_rate(self):
      return self.rate
      
   def schedule_entity(self, world, i_store):
      self.schedule_self(world, 0, i_store)

   def create_self_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)
         blob = actions.create_blob(world, self.get_name() + " -- blob",
            self.get_position(), self.get_rate() // BLOB_RATE_SCALE, 
            current_ticks, i_store)

         self.remove_entity(world)
         world.add_entity(blob)

         return [blob.get_position()]
      return action


class Quake(StaticEntity):
   def __init__(self, name, position, imgs, animation_rate):
      super(Quake, self).__init__(name, imgs, position)
      self.animation_rate = animation_rate
   
   def get_animation_rate(self):
      return self.animation_rate
   
   def schedule_self(self, world, ticks):
      self.schedule_animation(world, QUAKE_STEPS) 
      self.schedule_action(world, actions.create_entity_death_action(world, 
         self), ticks + QUAKE_DURATION)
